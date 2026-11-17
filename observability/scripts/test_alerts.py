"""Exercise the shipped Grafana PromQL with promtool, without any running service."""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

import yaml


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--promtool", default="promtool")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    group = yaml.safe_load((root / "chart/files/alerts.yaml").read_text(encoding="utf-8"))["groups"][0]
    rule = group["rules"][0]
    data = {item["refId"]: item for item in rule["data"]}
    condition = data[rule["condition"]]["model"]["conditions"][0]["evaluator"]
    if condition["type"] != "gt" or data["B"]["model"]["reducer"] != "last":
        raise ValueError("Update the test adapter if the Grafana condition changes")
    expression = data["A"]["model"]["expr"]
    generated = {"groups": [{"name": "grafana-contract", "interval": group["interval"], "rules": [{
        "alert": rule["title"], "expr": f"({expression}) > {condition['params'][0]}",
        "for": rule["for"], "labels": rule["labels"],
    }]}]}
    fixtures = yaml.safe_load((root / "tests/alert-cases.yaml").read_text(encoding="utf-8"))
    # Parse every dashboard PromQL with the same Prometheus version used in deployment.
    dashboard = json.loads((root / "chart/files/dashboard.json").read_text(encoding="utf-8"))
    recording_rules = []
    for panel in dashboard["panels"]:
        if panel.get("datasource", {}).get("type") == "prometheus":
            for target in panel["targets"]:
                recording_rules.append({"record": f"dashboard:panel_{panel['id']}",
                                        "expr": target["expr"].replace("$service", "evaluation-service")})
    generated["groups"].append({"name": "dashboard-syntax", "rules": recording_rules})
    with tempfile.TemporaryDirectory(prefix="fiap-promql-") as directory:
        destination = Path(directory)
        (destination / "rules.yaml").write_text(yaml.safe_dump(generated, allow_unicode=True), encoding="utf-8")
        fixtures["rule_files"] = ["rules.yaml"]
        (destination / "tests.yaml").write_text(yaml.safe_dump(fixtures, allow_unicode=True), encoding="utf-8")
        subprocess.run([args.promtool, "check", "rules", "rules.yaml"], cwd=destination, check=True)
        subprocess.run([args.promtool, "test", "rules", "tests.yaml"], cwd=destination, check=True)
    print(f"Passed {len(fixtures['tests'])} alert scenarios and parsed {len(recording_rules)} dashboard queries.")


if __name__ == "__main__":
    main()
