"""Read-only checks against the running local Compose stack; no cloud endpoints."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import boto3
import requests
from dotenv import dotenv_values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    configuration = dotenv_values(root / "observability/.env", interpolate=False)
    grafana = requests.Session()
    grafana.auth = ("admin", configuration["GF_SECURITY_ADMIN_PASSWORD"])

    def get_json(url, session=requests, **kwargs):
        response = session.get(url, timeout=10, **kwargs)
        response.raise_for_status()
        return response.json()

    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "environment": "local-compose"}
    report["services"] = {}
    for service, port in (("auth", 8001), ("flag", 8002), ("targeting", 8003), ("evaluation", 8004), ("analytics", 8005)):
        response = requests.get(f"http://127.0.0.1:{port}/health", timeout=5)
        response.raise_for_status()
        report["services"][service + "-service"] = response.status_code
    report["grafana_health"] = get_json("http://127.0.0.1:3000/api/health")["database"]
    dashboard = get_json("http://127.0.0.1:3000/api/dashboards/uid/togglemaster-phase4", grafana)
    report["dashboard"] = {"title": dashboard["dashboard"]["title"], "panels": len(dashboard["dashboard"]["panels"])}
    report["datasources"] = {}
    for datasource in ("prometheus", "loki"):
        report["datasources"][datasource] = get_json(f"http://127.0.0.1:3000/api/datasources/uid/{datasource}/health", grafana)["status"]
    metrics = get_json("http://127.0.0.1:9090/api/v1/query", params={"query": "sum by (service_name) (togglemaster_http_requests_total)"})
    report["http_requests_by_service"] = {item["metric"]["service_name"]: float(item["value"][1]) for item in metrics["data"]["result"]}
    report["log_services"] = get_json("http://127.0.0.1:3100/loki/api/v1/label/service_name/values")["data"]
    rules = get_json("http://127.0.0.1:3000/api/prometheus/grafana/api/v1/rules", grafana)
    report["alerts"] = [{"name": rule["name"], "state": rule["state"], "health": rule.get("health"),
                         "last_error": rule.get("lastError", "")}
                        for group in rules["data"]["groups"] for rule in group["rules"] if rule.get("type") == "alerting"]
    database = boto3.client("dynamodb", endpoint_url="http://127.0.0.1:8000", region_name="us-east-1",
                            aws_access_key_id="local", aws_secret_access_key="local")
    report["demo_events_in_dynamodb"] = database.scan(TableName="ToggleMasterAnalytics", Select="COUNT",
        FilterExpression="flag_name = :flag", ExpressionAttributeValues={":flag": {"S": "phase4-demo"}})["Count"]
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    assert report["grafana_health"] == "ok"
    assert report["dashboard"]["panels"] == 8
    assert all(status == "OK" for status in report["datasources"].values())
    assert {"auth-service", "flag-service", "targeting-service", "evaluation-service"} <= set(report["http_requests_by_service"])
    assert set(report["services"]) <= set(report["log_services"])
    assert report["demo_events_in_dynamodb"] > 0
    assert any(rule["name"] == "EvaluationHighErrorRate" and rule["health"] == "ok" for rule in report["alerts"])


if __name__ == "__main__":
    main()
