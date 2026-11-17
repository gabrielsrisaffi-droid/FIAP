"""Real Collector, local OTLP sink: metric names, query privacy and Loki routing."""

import gzip
import json
import os
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import requests
import yaml
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import ExportMetricsServiceRequest
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest


def port():
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        return server.getsockname()[1]


def test_collector_pipeline_contract(tmp_path):
    binary = os.environ.get("COLLECTOR_BINARY")
    if not binary:
        pytest.skip("Set COLLECTOR_BINARY to a verified otelcol-contrib binary")
    payloads = {}

    class Sink(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            if self.headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
            payloads.setdefault(self.path, []).append(body)
            self.send_response(200)
            self.send_header("Content-Type", "application/x-protobuf")
            self.end_headers()

        def log_message(self, *_args):
            pass

    sink = ThreadingHTTPServer(("127.0.0.1", 0), Sink)
    worker = threading.Thread(target=sink.serve_forever, daemon=True)
    worker.start()
    otlp, metrics_port, health, grpc = port(), port(), port(), port()
    repository = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((repository / "observability/chart/files/collector.yaml").read_text())
    config["extensions"]["health_check"]["endpoint"] = f"127.0.0.1:{health}"
    config["receivers"]["otlp"]["protocols"]["http"]["endpoint"] = f"127.0.0.1:{otlp}"
    config["receivers"]["otlp"]["protocols"]["grpc"]["endpoint"] = f"127.0.0.1:{grpc}"
    config["exporters"]["prometheus"]["endpoint"] = f"127.0.0.1:{metrics_port}"
    config["exporters"]["otlp_http/loki"]["endpoint"] = f"http://127.0.0.1:{sink.server_port}/otlp"
    config["exporters"]["otlp_http/test"] = {"endpoint": f"http://127.0.0.1:{sink.server_port}"}
    config["service"]["pipelines"]["traces"]["exporters"] = ["otlp_http/test"]
    config_path = tmp_path / "collector.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    log_path = tmp_path / "collector.log"
    with log_path.open("w", encoding="utf-8") as output:
        process = subprocess.Popen([binary, "--config=" + str(config_path)], stdout=output, stderr=output,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            deadline = time.monotonic() + 30
            while True:
                if process.poll() is not None:
                    pytest.fail(log_path.read_text(encoding="utf-8"))
                try:
                    if requests.get(f"http://127.0.0.1:{health}", timeout=1).ok:
                        break
                except requests.RequestException:
                    pass
                assert time.monotonic() < deadline, log_path.read_text(encoding="utf-8")
                time.sleep(0.1)
            now = time.time_ns()
            metrics = ExportMetricsServiceRequest()
            resource = metrics.resource_metrics.add()
            resource.resource.attributes.add(key="service.name").value.string_value = "evaluation-service"
            metric = resource.scope_metrics.add().metrics.add(name="togglemaster.http.requests")
            metric.sum.aggregation_temporality = 2
            metric.sum.is_monotonic = True
            point = metric.sum.data_points.add(as_int=30, start_time_unix_nano=now - 1000000000, time_unix_nano=now)
            point.attributes.add(key="http_response_status_code").value.int_value = 503
            duration = resource.scope_metrics[0].metrics.add(name="togglemaster.http.duration", unit="s")
            duration.histogram.aggregation_temporality = 2
            duration.histogram.data_points.add(count=1, sum=0.1, explicit_bounds=[0.5], bucket_counts=[1, 0],
                                               start_time_unix_nano=now - 1000000000, time_unix_nano=now)
            logs = ExportLogsServiceRequest()
            log_resource = logs.resource_logs.add()
            log_resource.resource.CopyFrom(resource.resource)
            log_resource.scope_logs.add().log_records.add(time_unix_nano=now).body.string_value = "controlled failure"
            traces = ExportTraceServiceRequest()
            trace_resource = traces.resource_spans.add()
            trace_resource.resource.CopyFrom(resource.resource)
            span = trace_resource.scope_spans.add().spans.add(name="/evaluate", trace_id=bytes.fromhex("11" * 16),
                     span_id=bytes.fromhex("22" * 8), start_time_unix_nano=now, end_time_unix_nano=now + 1000)
            span.attributes.add(key="url.full").value.string_value = "http://evaluation/evaluate?user_id=private"
            span.attributes.add(key="url.query").value.string_value = "user_id=private"
            for signal, payload in (("metrics", metrics), ("logs", logs), ("traces", traces)):
                response = requests.post(f"http://127.0.0.1:{otlp}/v1/{signal}", data=payload.SerializeToString(),
                                         headers={"Content-Type": "application/x-protobuf"}, timeout=5)
                response.raise_for_status()
            deadline = time.monotonic() + 15
            while True:
                exposition = requests.get(f"http://127.0.0.1:{metrics_port}/metrics", timeout=3).text
                if "togglemaster_http_requests_total" in exposition and {"/otlp/v1/logs", "/v1/traces"} <= payloads.keys():
                    break
                assert time.monotonic() < deadline, log_path.read_text(encoding="utf-8")
                time.sleep(0.2)
            assert 'http_response_status_code="503"' in exposition
            assert 'service_name="evaluation-service"' in exposition
            assert "togglemaster_http_duration_seconds_bucket" in exposition
            received = ExportTraceServiceRequest.FromString(payloads["/v1/traces"][0])
            attributes = received.resource_spans[0].scope_spans[0].spans[0].attributes
            values = {a.key: a.value.string_value for a in attributes}
            assert values["url.full"] == "http://evaluation/evaluate"
            assert "url.query" not in values
            dashboard = json.loads((repository / "observability/chart/files/dashboard.json").read_text(encoding="utf-8"))
            assert "togglemaster_http_duration_seconds_bucket" in json.dumps(dashboard)
        finally:
            process.terminate()
            process.wait(timeout=10)
            sink.shutdown()
            sink.server_close()
            worker.join(timeout=5)
