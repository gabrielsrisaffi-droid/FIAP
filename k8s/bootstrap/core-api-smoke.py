"""Bootstrap e smoke test de auth, flag e targeting pelo DNS do Kubernetes.

Entrada JSON: mode=issue-key com master_key, ou mode=smoke com api_key.
O chamador PowerShell injeta BOOTSTRAP_INPUT via stdin junto deste codigo.
Tambem pode ser executado como arquivo, recebendo o JSON por stdin.

IMPORTANTE: issue-key retorna a chave em stdout para captura EM MEMORIA pelo
chamador. Nunca executar esse modo com stdout exposto, tee ou redirecao a arquivo.
O modo smoke retorna apenas resultados sanitizados, sem credenciais.
"""

import json
import re
import sys

import requests


URLS = {
    "auth": "http://auth-service:8001",
    "flag": "http://flag-service:8002",
    "targeting": "http://targeting-service:8003",
}
FLAG_NAME = "demo-fiap-eks"
FLAG_DATA = {
    "name": FLAG_NAME,
    "description": "Demonstracao FIAP: teste integrado no EKS",
    "is_enabled": True,
}
# O evaluation-service recebido implementa PERCENTAGE, nao USER_LIST.
RULE_DATA = {
    "flag_name": FLAG_NAME,
    "is_enabled": True,
    "rules": {"type": "PERCENTAGE", "value": 100},
}


class SmokeFailure(Exception):
    """Mensagem controlada, sem headers, corpos de resposta ou credenciais."""


def request_api(session, method, service, path, expected, key=None, body=None):
    headers = {"Authorization": "Bearer " + key} if key else {}
    try:
        response = session.request(
            method,
            URLS[service] + path,
            headers=headers,
            json=body,
            timeout=(3, 10),
            allow_redirects=False,
        )
    except requests.RequestException:
        raise SmokeFailure("Falha de rede ao chamar " + service) from None
    if response.status_code not in expected:
        raise SmokeFailure(
            f"{service} {method} {path}: HTTP {response.status_code}; "
            f"esperado {sorted(expected)}"
        )
    return response


def object_body(response):
    try:
        data = response.json()
    except ValueError:
        raise SmokeFailure("Resposta HTTP sem JSON valido.") from None
    if not isinstance(data, dict):
        raise SmokeFailure("Formato de resposta inesperado.")
    return data


def require_fields(actual, expected, label):
    if any(actual.get(field) != value for field, value in expected.items()):
        raise SmokeFailure(
            label + ": dados diferentes dos esperados; nenhum registro existente sera sobrescrito."
        )


def ensure_demo(session, service, collection, item_path, expected, api_key):
    response = request_api(session, "GET", service, item_path, {200, 404}, api_key)
    if response.status_code == 404:
        response = request_api(session, "POST", service, collection, {201}, api_key, expected)
        require_fields(object_body(response), expected, service)
        action = "criada"
    else:
        require_fields(object_body(response), expected, service)
        action = "existente e preservada"
    # Nova chamada confirma leitura do registro persistido via API.
    response = request_api(session, "GET", service, item_path, {200}, api_key)
    require_fields(object_body(response), expected, service)
    return action


def run(config, session_factory=requests.Session):
    mode = config.get("mode")
    if mode not in {"issue-key", "smoke"}:
        raise SmokeFailure("Modo ausente ou invalido.")
    field = "master_key" if mode == "issue-key" else "api_key"
    pattern = r"[0-9a-f]{64}" if mode == "issue-key" else r"tm_key_[0-9a-f]{64}"
    key = config.get(field)
    if not isinstance(key, str) or re.fullmatch(pattern, key) is None:
        raise SmokeFailure("Credencial de entrada ausente ou em formato inesperado.")

    with session_factory() as session:
        # Nao encaminhar os Bearer tokens por proxies herdados do ambiente.
        session.trust_env = False
        if mode == "issue-key":
            request_api(session, "GET", "auth", "/health", {200})
            response = request_api(
                session, "POST", "auth", "/admin/keys", {201}, key,
                {"name": "evaluation-service-eks"},
            )
            api_key = object_body(response).get("key")
            if not isinstance(api_key, str) or re.fullmatch(r"tm_key_[0-9a-f]{64}", api_key) is None:
                raise SmokeFailure("Auth nao devolveu uma chave no formato esperado.")
            return {"api_key": api_key}

        checks = []
        for service in URLS:
            response = request_api(session, "GET", service, "/health", {200})
            require_fields(object_body(response), {"status": "ok"}, service)
            checks.append("PASS: " + service + " /health HTTP 200")

        for service, path in [
            ("auth", "/validate"),
            ("flag", "/flags"),
            ("targeting", "/rules/" + FLAG_NAME),
        ]:
            request_api(session, "GET", service, path, {401})
            checks.append("PASS: " + service + " sem chave HTTP 401")

        request_api(session, "GET", "auth", "/validate", {401}, "invalid-smoke-key")
        checks.append("PASS: auth rejeita chave invalida HTTP 401")

        request_api(
            session, "POST", "auth", "/admin/keys", {403},
            body={"name": "must-not-be-created"},
        )
        request_api(
            session, "POST", "auth", "/admin/keys", {403}, key,
            {"name": "must-not-be-created"},
        )
        checks.append("PASS: endpoint administrativo rejeita ausencia de MASTER_KEY e chave comum HTTP 403")

        request_api(session, "GET", "auth", "/validate", {200}, key)
        checks.append("PASS: chave da aplicacao validada HTTP 200")

        flag_action = ensure_demo(
            session, "flag", "/flags", "/flags/" + FLAG_NAME, FLAG_DATA, key
        )
        checks.append("PASS: flag " + flag_action + " e consultada pela API")
        rule_action = ensure_demo(
            session, "targeting", "/rules", "/rules/" + FLAG_NAME, RULE_DATA, key
        )
        checks.append("PASS: regra " + rule_action + " e consultada pela API")

        return {"status": "PASS", "checks": checks, "flag_name": FLAG_NAME, "rules": RULE_DATA["rules"]}


if __name__ == "__main__":
    try:
        config = globals().get("BOOTSTRAP_INPUT")
        if config is None:
            config = json.load(sys.stdin)
        result = run(config)
        print(json.dumps(result, ensure_ascii=True))
    except SmokeFailure as error:
        print("FAIL: " + str(error), file=sys.stderr)
        sys.exit(1)
    except Exception:
        # Nao imprimir excecoes arbitrarias que possam conter a configuracao.
        print("FAIL: erro inesperado no teste; preserve o estado para diagnostico.", file=sys.stderr)
        sys.exit(1)
