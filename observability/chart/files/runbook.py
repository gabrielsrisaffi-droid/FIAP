"""Authenticated Grafana webhook; only a fixed Kubernetes deployment can restart."""

import hmac
import json
import logging
import os
import re
import sqlite3
import ssl
import threading
import time
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LOGGER = logging.getLogger("togglemaster.runbook")


class RestartEngine:
    def __init__(self, database, restart, cooldown=300, clock=time.time):
        self.database, self.restart, self.cooldown, self.clock = database, restart, cooldown, clock
        self.lock = threading.Lock()
        with sqlite3.connect(self.database) as db:
            db.execute("CREATE TABLE IF NOT EXISTS actions (event TEXT PRIMARY KEY, attempted REAL, success INTEGER)")

    def process(self, payload):
        results = []
        for alert in payload.get("alerts", []):
            labels = alert.get("labels", {})
            if alert.get("status") != "firing" or labels.get("alertname") != "EvaluationHighErrorRate":
                results.append("ignored")
                continue
            if labels.get("service_name") != "evaluation-service" or labels.get("automation") != "restart-evaluation":
                results.append("ignored")
                continue
            fingerprint, started = alert.get("fingerprint", ""), alert.get("startsAt", "")
            if not isinstance(fingerprint, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,128}", fingerprint):
                results.append("invalid-fingerprint")
                continue
            try:
                began = datetime.fromisoformat(started.replace("Z", "+00:00")).timestamp()
            except (ValueError, TypeError, AttributeError):
                results.append("invalid-time")
                continue
            now = self.clock()
            if not -60 <= now - began <= 3600:
                results.append("stale-alert")
                continue
            event = fingerprint + ":" + started
            with self.lock, sqlite3.connect(self.database) as db:
                previous = db.execute("SELECT success FROM actions WHERE event = ?", (event,)).fetchone()
                latest = db.execute("SELECT MAX(attempted) FROM actions").fetchone()[0]
                if previous and previous[0]:
                    results.append("already-handled")
                    continue
                if latest is not None and now - latest < self.cooldown:
                    results.append("cooldown")
                    continue
                # Persist the attempt before issuing the API request. Failed attempts are also rate limited.
                db.execute("INSERT OR REPLACE INTO actions VALUES (?, ?, 0)", (event, now))
                db.commit()
                try:
                    self.restart()
                except Exception as error:
                    LOGGER.error("restart_failed error_type=%s", type(error).__name__)
                    raise
                db.execute("UPDATE actions SET success = 1 WHERE event = ?", (event,))
                db.execute("DELETE FROM actions WHERE attempted < ?", (now - 86400,))
                LOGGER.info("restart_requested fingerprint=%s", fingerprint)
                results.append("restart-requested")
        return results


def kubernetes_restart(namespace, deployment):
    for value in (namespace, deployment):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", value):
            raise ValueError("Invalid Kubernetes resource name")
    account = Path("/var/run/secrets/kubernetes.io/serviceaccount")
    token = (account / "token").read_text(encoding="utf-8").strip()
    context = ssl.create_default_context(cafile=str(account / "ca.crt"))
    timestamp = datetime.now(timezone.utc).isoformat()
    body = {"spec": {"template": {"metadata": {"annotations": {"togglemaster.fiap/restartedAt": timestamp}}}}}
    request = urllib.request.Request(
        f"https://kubernetes.default.svc/apis/apps/v1/namespaces/{namespace}/deployments/{deployment}",
        data=json.dumps(body).encode(), method="PATCH",
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/merge-patch+json"},
    )
    # URL is the fixed HTTPS Kubernetes endpoint, never supplied by the webhook.
    with urllib.request.urlopen(request, context=context, timeout=15) as response:  # nosec B310
        if response.status != 200:
            raise RuntimeError("Kubernetes rejected restart")


def make_handler(engine, token):
    if len(token) < 32:
        raise ValueError("RUNBOOK_TOKEN must have at least 32 characters")

    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, body):
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self.respond(200 if self.path == "/health" else 404, {"status": "ok" if self.path == "/health" else "not-found"})

        def do_POST(self):
            if self.path != "/grafana":
                return self.respond(404, {"error": "not-found"})
            if not hmac.compare_digest(self.headers.get("Authorization", "").encode(), ("Bearer " + token).encode()):
                return self.respond(401, {"error": "unauthorized"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 65536:
                    return self.respond(413, {"error": "invalid-size"})
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict) or not isinstance(payload.get("alerts"), list):
                    raise ValueError("invalid payload")
                if not all(isinstance(a, dict) and isinstance(a.get("labels", {}), dict) for a in payload["alerts"]):
                    raise ValueError("invalid alerts")
            except (ValueError, UnicodeDecodeError):
                return self.respond(400, {"error": "invalid-json"})
            try:
                return self.respond(200, {"results": engine.process(payload)})
            except Exception:
                return self.respond(503, {"error": "restart-failed"})

        def log_message(self, fmt, *args):
            LOGGER.info(fmt, *args)

    return Handler


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    namespace = os.environ["APPLICATION_NAMESPACE"]
    deployment = os.environ["TARGET_DEPLOYMENT"]
    engine = RestartEngine(os.getenv("STATE_FILE", "/state/actions.db"),
                           lambda: kubernetes_restart(namespace, deployment),
                           cooldown=max(60, int(os.getenv("COOLDOWN_SECONDS", "300"))))
    # Kubernetes ClusterIP must reach the pod; requests require the shared bearer token.
    server = ThreadingHTTPServer(("0.0.0.0", 8080), make_handler(engine, os.environ["RUNBOOK_TOKEN"]))  # nosec B104
    server.serve_forever()


if __name__ == "__main__":
    main()
