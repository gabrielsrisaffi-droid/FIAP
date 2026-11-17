"""Check local configuration for the lab. Never contacts AWS or prints secret values."""

import argparse
import re
import subprocess
import urllib.parse
from pathlib import Path

from dotenv import dotenv_values


def check_secrets(path, integrations):
    required = ["GF_SECURITY_ADMIN_PASSWORD"]
    if integrations:
        required += ["NEW_RELIC_LICENSE_KEY", "PAGERDUTY_ROUTING_KEY", "PAGERDUTY_API_TOKEN",
                     "PAGERDUTY_SERVICE_ID", "DISCORD_WEBHOOK_URL", "RUNBOOK_TOKEN"]
    if not path.is_file():
        return [("PENDENTE", "Arquivo de configuração local ausente; criar a partir de secrets.env.example.")]
    # Do not expand environment variables or echo values/errors containing credentials.
    values = dotenv_values(path, interpolate=False)
    results = []
    placeholders = ("SUBSTITUIR", "CHANGEME", "YOUR_", "PLACEHOLDER")
    for key in required:
        value = values.get(key) or ""
        valid = bool(value.strip()) and not any(word in value.upper() for word in placeholders)
        if key == "RUNBOOK_TOKEN":
            valid = valid and len(value) >= 32 and not any(char.isspace() for char in value)
        if key == "GF_SECURITY_ADMIN_PASSWORD":
            valid = valid and len(value) >= 12
        if key == "DISCORD_WEBHOOK_URL" and valid:
            url = urllib.parse.urlparse(value)
            valid = (url.scheme == "https" and url.netloc == "discord.com"
                     and re.fullmatch(r"/api/webhooks/[0-9]+/[A-Za-z0-9._-]+", url.path) is not None)
        results.append(("OK" if valid else "PENDENTE", key + (": preenchido" if valid else ": ausente, exemplo ou formato inválido")))
    if integrations and values.get("PAGERDUTY_ROUTING_KEY") and values.get("PAGERDUTY_ROUTING_KEY") == values.get("PAGERDUTY_API_TOKEN"):
        results.append(("PENDENTE", "PagerDuty: routing key e token REST precisam ser credenciais distintas."))
    return results


def main():
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--secrets", type=Path, default=root / "observability/.env")
    parser.add_argument("--integrations", action="store_true", help="Include APM, incidents, Discord and self-healing requirements")
    args = parser.parse_args()
    path = args.secrets.resolve()
    results = check_secrets(path, args.integrations)
    if path.is_relative_to(root) and path.exists():
        relative = path.relative_to(root).as_posix()
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "--", relative], cwd=root, capture_output=True).returncode == 0
        ignored = subprocess.run(["git", "check-ignore", "-q", "--", relative], cwd=root, capture_output=True).returncode == 0
        results.append(("OK" if ignored and not tracked else "PENDENTE",
                        "Arquivo de credenciais ignorado e fora do versionamento." if ignored and not tracked else
                        "Retirar o arquivo de credenciais do versionamento e verificar o .gitignore antes de publicar."))
    for status, message in results:
        print(f"[{status}] {message}")
    print("Verificação somente local. Valores não foram exibidos; validade das contas e chaves ainda precisa ser confirmada nas ferramentas.")
    return 2 if any(status != "OK" for status, _ in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
