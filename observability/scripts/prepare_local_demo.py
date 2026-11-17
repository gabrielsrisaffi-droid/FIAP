"""Seed only the local Compose database and create synthetic demo data."""

import hashlib
import json
import subprocess
from pathlib import Path

import requests

root = Path(__file__).resolve().parents[2]
compose = ["docker", "compose", "--project-directory", str(root), "-f", str(root / "docker-compose.yml"),
           "-f", str(root / "observability/local/apps.override.yaml")]
configuration = json.loads(subprocess.run(compose + ["config", "--format", "json"],
                                           check=True, capture_output=True, text=True).stdout)
# Use the local service's actual key without printing it or writing it to a file.
key = configuration["services"]["evaluation-service"]["environment"]["SERVICE_API_KEY"]
digest = hashlib.sha256(key.encode()).hexdigest()
statement = "INSERT INTO api_keys (name,key_hash,is_active) VALUES ('fase4-local', '" + digest + "', true) ON CONFLICT (key_hash) DO UPDATE SET is_active=true;"
subprocess.run(compose + ["exec", "-T", "postgres-auth", "sh", "-c",
               'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'],
               input=statement, text=True, check=True, capture_output=True)
headers = {"Authorization": "Bearer " + key}
for url, body in (
    ("http://127.0.0.1:8002/flags", {"name": "phase4-demo", "description": "Synthetic observability test", "is_enabled": True}),
    ("http://127.0.0.1:8003/rules", {"flag_name": "phase4-demo", "is_enabled": True, "rules": {"type": "PERCENTAGE", "value": 100}}),
):
    response = requests.post(url, json=body, headers=headers, timeout=10)
    if response.status_code not in (201, 409):
        raise RuntimeError("Demo setup failed with HTTP " + str(response.status_code))
response = requests.get("http://127.0.0.1:8004/evaluate", params={"user_id": "synthetic-user", "flag_name": "phase4-demo"}, timeout=10)
response.raise_for_status()
assert response.json()["result"] is True, "Existing demo flag/rule differs from the expected enabled configuration"
print("Local demo prepared and evaluation returned true. No credentials were printed.")
