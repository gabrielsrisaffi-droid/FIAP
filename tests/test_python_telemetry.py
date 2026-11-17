"""Run once per Python service build context using SERVICE_DIRECTORY."""

import atexit
import importlib.util
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests

from flask import Flask
from opentelemetry import trace
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import ExportMetricsServiceRequest
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest


def test_three_signals_and_message_context(monkeypatch):
    directory = Path(os.environ["SERVICE_DIRECTORY"])
    spec = importlib.util.spec_from_file_location("service_telemetry", directory / "telemetry.py")
    telemetry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(telemetry)
    payloads = {}
    outbound_headers = []

    class Receiver(BaseHTTPRequestHandler):
        def do_GET(self):
            outbound_headers.append(self.headers.get("traceparent"))
            self.send_response(200)
            self.end_headers()

        def do_POST(self):
            payloads.setdefault(self.path, []).append(self.rfile.read(int(self.headers["Content-Length"])))
            self.send_response(200)
            self.send_header("Content-Type", "application/x-protobuf")
            self.end_headers()

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Receiver)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setenv("OTEL_SDK_DISABLED", "false")
    monkeypatch.setenv("OTEL_METRIC_EXPORT_INTERVAL", "60000")
    logging.getLogger().setLevel(logging.INFO)
    shutdown = telemetry.configure_telemetry("python-test-service")
    app = Flask(__name__)
    telemetry.instrument_flask(app, "python-test-service")

    @app.route("/items/<item>")
    def failed_request(item):
        requests.get(f"http://127.0.0.1:{server.server_port}/dependency", timeout=3).raise_for_status()
        return "unavailable", 503

    @app.route("/health")
    def health():
        return "ok"

    traceparent = "00-11111111111111111111111111111111-2222222222222222-01"
    try:
        client = app.test_client()
        response = client.get("/items/private-id", headers={"traceparent": traceparent})
        assert response.status_code == 503
        assert client.get("/health").status_code == 200
        context = telemetry.message_context({"MessageAttributes": {
            "traceparent": {"StringValue": traceparent, "DataType": "String"},
        }})
        with trace.get_tracer("probe").start_as_current_span("consume", context=context) as span:
            assert span.get_span_context().trace_id == int("11" * 16, 16)
            # Legacy queue messages must not inherit a previous message's trace.
            assert not trace.get_current_span(telemetry.message_context({})).get_span_context().is_valid
        shutdown()
        atexit.unregister(shutdown)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert set(payloads) == {"/v1/traces", "/v1/metrics", "/v1/logs"}
    assert len(outbound_headers) == 1 and "11" * 16 in outbound_headers[0]
    spans = []
    for body in payloads["/v1/traces"]:
        request = ExportTraceServiceRequest.FromString(body)
        spans.extend(span for resource in request.resource_spans for scope in resource.scope_spans for span in scope.spans)
    assert any(span.name == "GET /items/<item>" and span.trace_id == bytes.fromhex("11" * 16) for span in spans)
    assert not any("health" in span.name for span in spans)
    counters = []
    for body in payloads["/v1/metrics"]:
        request = ExportMetricsServiceRequest.FromString(body)
        counters.extend(metric for resource in request.resource_metrics for scope in resource.scope_metrics
                        for metric in scope.metrics if metric.name == "togglemaster.http.requests")
    assert len(counters) == 1
    assert counters[0].sum.data_points[0].as_int == 1
    labels = {a.key: a.value.string_value for a in counters[0].sum.data_points[0].attributes}
    assert labels["http_route"] == "/items/<item>"
    entries = []
    for body in payloads["/v1/logs"]:
        request = ExportLogsServiceRequest.FromString(body)
        entries.extend(record for resource in request.resource_logs for scope in resource.scope_logs for record in scope.log_records)
    assert any(record.trace_id == bytes.fromhex("11" * 16) for record in entries)
