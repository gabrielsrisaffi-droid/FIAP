"""Create local Grafana/runbook credentials once, without displaying their values."""

import secrets
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[2]
destination = root / "observability/.env"
if destination.exists():
    print("Local environment already exists; preserved without changes.")
    raise SystemExit(0)
ignored = subprocess.run(["git", "check-ignore", "-q", "--", "observability/.env"], cwd=root).returncode == 0
if not ignored:
    raise SystemExit("Refusing to create credentials: observability/.env must be ignored by Git.")
content = (root / "observability/secrets.env.example").read_text(encoding="utf-8")
for name in ("GF_SECURITY_ADMIN_PASSWORD", "RUNBOOK_TOKEN"):
    content = content.replace(name + "=\n", name + "=" + secrets.token_urlsafe(36) + "\n")
with destination.open("x", encoding="utf-8") as output:
    output.write(content)
print("Local environment created. Grafana/runbook credentials generated; external account fields remain empty.")
