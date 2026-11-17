"""Inject and remove the lab fault; verify real Grafana firing/resolution under existing local load."""

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import dotenv_values


def main():
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    configuration = dotenv_values(root / "observability/.env", interpolate=False)
    grafana = requests.Session()
    grafana.auth = ("admin", configuration["GF_SECURITY_ADMIN_PASSWORD"])
    compose = ["docker", "--context", "desktop-linux", "compose", "-f", str(root / "docker-compose.yml"),
               "-f", str(root / "observability/local/apps.override.yaml"), "exec", "-T", "evaluation-service"]
    report = {"environment": "local-compose", "recovery_action": "manual removal of lab fault; no Kubernetes automation", "events": []}

    def record(event, **details):
        row = {"time": datetime.now(timezone.utc).isoformat(), "event": event, **details}
        report["events"].append(row)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(row), flush=True)

    def evaluation():
        return requests.get("http://127.0.0.1:8004/evaluate", params={"user_id": "synthetic-alert-probe", "flag_name": "phase4-demo"}, timeout=10).status_code

    def wait_for_state(expected, timeout):
        deadline, last = time.monotonic() + timeout, None
        while time.monotonic() < deadline:
            response = grafana.get("http://127.0.0.1:3000/api/prometheus/grafana/api/v1/rules", timeout=10)
            response.raise_for_status()
            rules = [r for g in response.json()["data"]["groups"] for r in g["rules"] if r["name"] == "EvaluationHighErrorRate"]
            if len(rules) != 1 or rules[0].get("health") != "ok":
                raise RuntimeError("Grafana rule unavailable or unhealthy")
            state = rules[0]["state"]
            if state != last:
                record("alert_state", state=state)
                last = state
            if state == expected:
                return
            time.sleep(10)
        raise TimeoutError("Expected Grafana state was not observed: " + expected)

    assert evaluation() == 200, "Local evaluation must be healthy before injection"
    subprocess.run(compose + ["test", "!", "-e", "/tmp/togglemaster-fault"], check=True, capture_output=True)
    created = False
    try:
        subprocess.run(compose + ["touch", "/tmp/togglemaster-fault"], check=True, capture_output=True)
        created = True
        record("fault_injected")
        assert evaluation() == 503
        record("evaluation_failed", status=503)
        wait_for_state("firing", 180)
        subprocess.run(compose + ["rm", "/tmp/togglemaster-fault"], check=True, capture_output=True)
        created = False
        record("fault_removed_manually")
        assert evaluation() == 200
        record("evaluation_recovered", status=200)
        wait_for_state("inactive", 240)
        record("local_alert_cycle_completed")
    finally:
        if created:
            subprocess.run(compose + ["rm", "-f", "/tmp/togglemaster-fault"], check=True, capture_output=True)
            record("fault_removed_on_exit")


if __name__ == "__main__":
    main()
