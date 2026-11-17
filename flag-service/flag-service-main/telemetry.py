"""OTLP/HTTP telemetry. Kept identical in the three Python build contexts."""

import atexit
import logging
import os
import time

from flask import g, request
from opentelemetry import metrics, trace
from opentelemetry.context import Context
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


class ApplicationLogFilter(logging.Filter):
    def filter(self, record):
        # Exporter errors must not recursively export themselves.
        return not record.name.startswith(("opentelemetry", "urllib3"))


def configure_telemetry(service):
    if not os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or os.getenv("OTEL_SDK_DISABLED") == "true":
        return
    resource = Resource.create({"service.name": service})
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[PeriodicExportingMetricReader(OTLPMetricExporter())],
    )
    metrics.set_meter_provider(meter_provider)
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    handler.addFilter(ApplicationLogFilter())
    logging.getLogger().addHandler(handler)
    RequestsInstrumentor().instrument()

    def shutdown():
        logging.getLogger().removeHandler(handler)
        for provider in (tracer_provider, meter_provider, logger_provider):
            provider.shutdown()

    atexit.register(shutdown)
    return shutdown


def instrument_flask(app, service):
    FlaskInstrumentor().instrument_app(app, excluded_urls=r"/health$")
    meter = metrics.get_meter("togglemaster.http")
    counter = meter.create_counter("togglemaster.http.requests")
    duration = meter.create_histogram("togglemaster.http.duration", unit="s",
                                      explicit_bucket_boundaries_advisory=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10])

    @app.before_request
    def request_start():
        g.telemetry_start = time.monotonic()

    @app.after_request
    def request_end(response):
        if request.path == "/health":
            return response
        route = request.url_rule.rule if request.url_rule else "unmatched"
        attributes = {
            "http_route": route,
            "http_request_method": request.method,
            "http_response_status_code": response.status_code,
        }
        counter.add(1, attributes)
        duration.record(time.monotonic() - g.telemetry_start, attributes)
        level = logging.ERROR if response.status_code >= 500 else logging.INFO
        logging.getLogger("togglemaster.http").log(level, "HTTP request completed", extra={**attributes, "service_name": service})
        return response


def message_context(message):
    attributes = message.get("MessageAttributes", {})
    carrier = {
        key: value["StringValue"]
        for key, value in attributes.items()
        if key in ("traceparent", "tracestate") and "StringValue" in value
    }
    # Each queue message starts from a clean context, including legacy messages.
    return TraceContextTextMapPropagator().extract(carrier, context=Context())
