"""Relay incident state from one PagerDuty service to Discord using outbound HTTPS."""

import json
import logging
import os
import sqlite3
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

LOGGER = logging.getLogger("togglemaster.discord")


def list_incidents(api_key, service_id):
    incidents, offset = [], 0
    since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    while True:
        query = urllib.parse.urlencode({"service_ids[]": service_id, "since": since,
                                        "limit": 100, "offset": offset})
        request = urllib.request.Request("https://api.pagerduty.com/incidents?" + query, headers={
            "Authorization": "Token token=" + api_key,
            "Accept": "application/vnd.pagerduty+json;version=2",
        })
        # URL uses the fixed official HTTPS API, not incident data.
        with urllib.request.urlopen(request, timeout=15) as response:  # nosec B310
            data = json.load(response)
        incidents.extend(i for i in data["incidents"] if i.get("service", {}).get("id") == service_id)
        if not data.get("more"):
            return incidents
        offset += 100
        if offset >= 1000:
            raise RuntimeError("Incident volume exceeds laboratory limit")


def send_discord(webhook, incident):
    url = urllib.parse.urlparse(webhook)
    if url.scheme != "https" or url.netloc != "discord.com" or not url.path.startswith("/api/webhooks/"):
        raise ValueError("Expected an official Discord HTTPS webhook")
    body = {"content": "[FIAP] Incidente PagerDuty " + str(incident["id"]) + " — " + str(incident["status"])
            + "\n" + str(incident.get("title", "EvaluationHighErrorRate"))[:500],
            "allowed_mentions": {"parse": []}}
    request = urllib.request.Request(webhook, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "User-Agent": "FIAP-Incident-Bridge/1.0"})
    # Host and HTTPS scheme were validated above.
    with urllib.request.urlopen(request, timeout=15) as response:  # nosec B310
        if response.status not in (200, 204):
            raise RuntimeError("Discord rejected notification")


def sync_incidents(database, incidents, notify):
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE IF NOT EXISTS incidents (id TEXT PRIMARY KEY, status TEXT)")
        for incident in incidents:
            incident_id, status = incident["id"], incident["status"]
            if status not in ("triggered", "acknowledged", "resolved"):
                continue
            previous = db.execute("SELECT status FROM incidents WHERE id = ?", (incident_id,)).fetchone()
            if previous and previous[0] == status:
                continue
            # Do not announce already resolved historical incidents on first startup.
            if previous or status != "resolved":
                notify(incident)
                LOGGER.info("discord_notified incident=%s status=%s", incident_id, status)
            db.execute("INSERT OR REPLACE INTO incidents VALUES (?, ?)", (incident_id, status))
            db.commit()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    api_key = os.environ["PAGERDUTY_API_TOKEN"]
    service_id = os.environ["PAGERDUTY_SERVICE_ID"]
    webhook = os.environ["DISCORD_WEBHOOK_URL"]
    database = os.getenv("STATE_FILE", "/state/discord.db")
    while True:
        try:
            sync_incidents(database, list_incidents(api_key, service_id), lambda i: send_discord(webhook, i))
        except Exception as error:
            LOGGER.error("bridge_cycle_failed error_type=%s", type(error).__name__)
        time.sleep(30)


if __name__ == "__main__":
    main()
