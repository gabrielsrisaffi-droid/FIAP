"""Generate the provisioned Grafana dashboard. No external services are accessed."""

import json
from pathlib import Path

PANELS = []
PROM = {"type": "prometheus", "uid": "prometheus"}
SELECTOR = 'service_name=~"$service"'


def panel(title, expression, unit, x, y, width=12, height=8, kind="timeseries", legend="{{service_name}}"):
    PANELS.append({
        "id": len(PANELS) + 1, "title": title, "type": kind, "datasource": PROM,
        "gridPos": {"x": x, "y": y, "w": width, "h": height},
        "fieldConfig": {"defaults": {"unit": unit, "min": 0}, "overrides": []},
        "options": {"legend": {"displayMode": "list", "placement": "bottom"}},
        "targets": [{"refId": "A", "expr": expression, "legendFormat": legend}],
    })


panel("Requisições por segundo", f'sum(rate(togglemaster_http_requests_total{{{SELECTOR}}}[2m]))',
      "reqps", 0, 0, 8, 4, "stat")
panel("Erros 5xx (%)", f'(sum(rate(togglemaster_http_requests_total{{{SELECTOR},http_response_status_code=~"5.."}}[2m])) or vector(0)) / clamp_min(sum(rate(togglemaster_http_requests_total{{{SELECTOR}}}[2m])), 0.001) * 100',
      "percent", 8, 0, 8, 4, "stat")
panel("Latência p95", f'histogram_quantile(0.95, sum by (le) (rate(togglemaster_http_duration_seconds_bucket{{{SELECTOR}}}[2m])))',
      "s", 16, 0, 8, 4, "stat")
panel("Volume por serviço", f'sum by (service_name) (rate(togglemaster_http_requests_total{{{SELECTOR}}}[2m]))', "reqps", 0, 4)
panel("Respostas 5xx por serviço", f'sum by (service_name) (rate(togglemaster_http_requests_total{{{SELECTOR},http_response_status_code=~"5.."}}[2m]))', "reqps", 12, 4)
panel("CPU por pod (cores) — Kubernetes", 'sum by (k8s_pod_name) ({__name__=~"k8s_pod_cpu_usage(_.*)?",k8s_namespace_name="togglemaster",k8s_pod_name=~"($service)-.*"})', "cores", 0, 12, legend="{{k8s_pod_name}}")
panel("Memória por pod — Kubernetes", 'sum by (k8s_pod_name) (k8s_pod_memory_usage_bytes{k8s_namespace_name="togglemaster",k8s_pod_name=~"($service)-.*"})', "bytes", 12, 12, legend="{{k8s_pod_name}}")
PANELS.append({"id": 8, "title": "Logs de aplicação — abra o Explore para Live tail",
               "type": "logs", "datasource": {"type": "loki", "uid": "loki"},
               "gridPos": {"x": 0, "y": 20, "w": 24, "h": 10},
               "options": {"showTime": True, "wrapLogMessage": True, "sortOrder": "Descending", "enableLogDetails": True},
               "targets": [{"refId": "A", "expr": '{service_name=~"$service"}', "queryType": "range"}]})
DASHBOARD = {
    "uid": "togglemaster-phase4", "title": "ToggleMaster | Fase 4", "schemaVersion": 39,
    "version": 1, "timezone": "browser", "refresh": "10s", "time": {"from": "now-15m", "to": "now"},
    "tags": ["fiap", "togglemaster", "otel"], "editable": False,
    "description": "Métricas e logs OTLP dos cinco serviços. CPU/memória requerem kubeletstats no cluster; não estão disponíveis no Compose local.",
    "templating": {"list": [{"name": "service", "label": "Serviço", "type": "custom", "multi": True,
                              "includeAll": True, "allValue": ".+", "query": "auth-service,flag-service,targeting-service,evaluation-service,analytics-service",
                              "current": {"text": "All", "value": "$__all"}}]},
    "panels": PANELS,
}
destination = Path(__file__).resolve().parents[1] / "chart" / "files" / "dashboard.json"
destination.write_text(json.dumps(DASHBOARD, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(destination)
