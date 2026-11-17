import importlib.util
from datetime import datetime, timezone
from pathlib import Path

import pytest


def load_module(name):
    path = Path(__file__).resolve().parents[1] / "observability" / "chart" / "files" / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runbook = load_module("runbook")
bridge = load_module("discord_bridge")


def alert(now, **changes):
    value = {"status": "firing", "fingerprint": "abc123", "startsAt": datetime.fromtimestamp(now, timezone.utc).isoformat(),
             "labels": {"alertname": "EvaluationHighErrorRate", "service_name": "evaluation-service", "automation": "restart-evaluation"}}
    value.update(changes)
    return {"alerts": [value]}


def test_restart_is_idempotent_and_persisted(tmp_path):
    now, calls = 1000000, []
    database = str(tmp_path / "actions.db")
    engine = runbook.RestartEngine(database, lambda: calls.append("restart"), clock=lambda: now)
    assert engine.process(alert(now)) == ["restart-requested"]
    engine = runbook.RestartEngine(database, lambda: calls.append("restart"), clock=lambda: now + 600)
    assert engine.process(alert(now)) == ["already-handled"]
    assert calls == ["restart"]


@pytest.mark.parametrize("changes", [
    {"status": "resolved"}, {"labels": {"service_name": "auth-service"}},
    {"startsAt": "invalid"}, {"fingerprint": ""},
])
def test_non_actionable_alerts_never_restart(tmp_path, changes):
    calls = []
    engine = runbook.RestartEngine(str(tmp_path / "actions.db"), lambda: calls.append(1), clock=lambda: 1000000)
    engine.process(alert(1000000, **changes))
    assert not calls


def test_cooldown_and_stale_replays(tmp_path):
    now, calls = [1000000], []
    engine = runbook.RestartEngine(str(tmp_path / "actions.db"), lambda: calls.append(1), clock=lambda: now[0])
    engine.process(alert(now[0]))
    now[0] += 20
    assert engine.process(alert(now[0], fingerprint="different")) == ["cooldown"]
    assert engine.process(alert(now[0] - 4000)) == ["stale-alert"]
    assert len(calls) == 1


def test_failed_restart_can_retry_after_cooldown(tmp_path):
    now, calls = [1000000], []

    def restart():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("Kubernetes unavailable")

    engine = runbook.RestartEngine(str(tmp_path / "actions.db"), restart, clock=lambda: now[0])
    payload = alert(now[0])
    with pytest.raises(RuntimeError):
        engine.process(payload)
    assert engine.process(payload) == ["cooldown"]
    now[0] += 301
    assert engine.process(payload) == ["restart-requested"]


def test_webhook_authentication_and_payload_validation(tmp_path):
    import threading
    from http.server import ThreadingHTTPServer

    import requests

    calls = []
    engine = runbook.RestartEngine(str(tmp_path / "actions.db"), lambda: calls.append(1))
    token = "test-only-not-a-real-secret-123456789"
    server = ThreadingHTTPServer(("127.0.0.1", 0), runbook.make_handler(engine, token))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{server.server_port}/grafana"
    headers = {"Authorization": "Bearer " + token}
    try:
        assert requests.post(url, json=alert(datetime.now(timezone.utc).timestamp()), timeout=3).status_code == 401
        assert requests.post(url, headers=headers, json={"alerts": [None]}, timeout=3).status_code == 400
        assert requests.post(url, headers=headers, json=alert(datetime.now(timezone.utc).timestamp()), timeout=3).status_code == 200
        assert calls == [1]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def test_discord_receives_incident_transitions_once(tmp_path):
    calls, database = [], str(tmp_path / "discord.db")
    incident = {"id": "PDTEST", "status": "triggered"}
    bridge.sync_incidents(database, [incident], lambda i: calls.append(i["status"]))
    bridge.sync_incidents(database, [incident], lambda i: calls.append(i["status"]))
    bridge.sync_incidents(database, [{**incident, "status": "resolved"}], lambda i: calls.append(i["status"]))
    assert calls == ["triggered", "resolved"]


def test_discord_delivery_failure_is_retried(tmp_path):
    database, incident = str(tmp_path / "discord.db"), {"id": "PDTEST", "status": "triggered"}

    def fail(_incident):
        raise RuntimeError("Discord unavailable")

    with pytest.raises(RuntimeError):
        bridge.sync_incidents(database, [incident], fail)
    delivered = []
    bridge.sync_incidents(database, [incident], delivered.append)
    assert delivered == [incident]


def test_repeated_webhook_recovers_after_temporary_kubernetes_failure(tmp_path):
    import threading
    from http.server import ThreadingHTTPServer

    import requests

    now, calls = [1000000], []

    def restart():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("temporary API failure")

    engine = runbook.RestartEngine(str(tmp_path / "actions.db"), restart, clock=lambda: now[0])
    token = "test-only-not-a-real-secret-123456789"
    server = ThreadingHTTPServer(("127.0.0.1", 0), runbook.make_handler(engine, token))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{server.server_port}/grafana"
    headers = {"Authorization": "Bearer " + token}
    payload = alert(now[0])
    try:
        assert requests.post(url, headers=headers, json=payload, timeout=3).status_code == 503
        # Grafana's self-healing route repeats each minute; the engine enforces its five-minute cooldown.
        now[0] += 60
        assert requests.post(url, headers=headers, json=payload, timeout=3).json()["results"] == ["cooldown"]
        now[0] += 240
        assert requests.post(url, headers=headers, json=payload, timeout=3).json()["results"] == ["restart-requested"]
        now[0] += 60
        assert requests.post(url, headers=headers, json=payload, timeout=3).json()["results"] == ["already-handled"]
        assert len(calls) == 2
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
