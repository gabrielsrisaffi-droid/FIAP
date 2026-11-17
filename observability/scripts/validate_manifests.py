"""Offline structure checks on rendered Helm and Kustomize manifests."""

import argparse
import json
from pathlib import Path

import yaml

parser = argparse.ArgumentParser()
parser.add_argument("chart")
parser.add_argument("apps")
args = parser.parse_args()
documents = [d for d in yaml.safe_load_all(Path(args.chart).read_text(encoding="utf-8")) if d]
identities = [(d["kind"], d["metadata"].get("namespace", "observability"), d["metadata"]["name"]) for d in documents]
assert len(identities) == len(set(identities)), "Duplicate Kubernetes resources"
for document in documents:
    if document["kind"] == "ConfigMap":
        for key, value in document["data"].items():
            if key.endswith(".yaml"):
                parsed = yaml.safe_load(value)
                if key == "contacts.yaml":
                    for route in parsed["policies"][0]["routes"]:
                        if route["receiver"] == "self-healing":
                            assert route["repeat_interval"] == "1m", "Remediation retries must recur within cooldown/staleness limits"
            elif key.endswith(".json"):
                json.loads(value)
    if document["kind"] == "Role" and document["metadata"]["name"] == "incident-runbook":
        assert document["rules"] == [{"apiGroups": ["apps"], "resources": ["deployments"],
                                       "resourceNames": ["evaluation-service"], "verbs": ["get", "patch"]}]
apps = [d for d in yaml.safe_load_all(Path(args.apps).read_text(encoding="utf-8")) if d and d["kind"] == "Deployment"]
assert len(apps) == 5
for app in apps:
    variables = app["spec"]["template"]["spec"]["containers"][0]["env"]
    names = [v["name"] for v in variables]
    assert len(names) == len(set(names)), f"Duplicate env in {app['metadata']['name']}"
    assert "OTEL_EXPORTER_OTLP_ENDPOINT" in names
print(f"Validated {len(documents)} chart resources and telemetry settings for {len(apps)} deployments.")
