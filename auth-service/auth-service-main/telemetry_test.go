package main

import (
	"bytes"
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"

	logspb "go.opentelemetry.io/proto/otlp/collector/logs/v1"
	metricspb "go.opentelemetry.io/proto/otlp/collector/metrics/v1"
	tracespb "go.opentelemetry.io/proto/otlp/collector/trace/v1"
	"google.golang.org/protobuf/proto"
)

func TestTelemetryExportsThreeSignals(t *testing.T) {
	var mu sync.Mutex
	payloads := map[string][][]byte{}
	collector := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		body, err := io.ReadAll(r.Body)
		if err != nil {
			t.Error(err)
		}
		mu.Lock()
		payloads[r.URL.Path] = append(payloads[r.URL.Path], body)
		mu.Unlock()
		w.Header().Set("Content-Type", "application/x-protobuf")
		w.WriteHeader(http.StatusOK)
	}))
	defer collector.Close()
	t.Setenv("OTEL_EXPORTER_OTLP_ENDPOINT", collector.URL)
	t.Setenv("OTEL_SDK_DISABLED", "false")
	shutdown, err := setupTelemetry("test-service")
	if err != nil {
		t.Fatal(err)
	}
	handler := instrumentHandler("test-service", "/items/{id}", http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	req := httptest.NewRequest(http.MethodGet, "/items/private-id?token=do-not-export", nil)
	req.Header.Set("traceparent", "00-11111111111111111111111111111111-2222222222222222-01")
	result := httptest.NewRecorder()
	handler.ServeHTTP(result, req)
	if result.Code != http.StatusServiceUnavailable {
		t.Fatalf("response changed: %d", result.Code)
	}
	instrumentHandler("test-service", "/health", http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
	})).ServeHTTP(httptest.NewRecorder(), httptest.NewRequest(http.MethodGet, "/health", nil))
	if err := shutdown(context.Background()); err != nil {
		t.Fatal(err)
	}
	mu.Lock()
	defer mu.Unlock()
	for _, signal := range []string{"traces", "metrics", "logs"} {
		if len(payloads["/v1/"+signal]) == 0 {
			t.Fatalf("missing OTLP %s", signal)
		}
	}
	var traceRequest tracespb.ExportTraceServiceRequest
	if err := proto.Unmarshal(payloads["/v1/traces"][0], &traceRequest); err != nil {
		t.Fatal(err)
	}
	span := traceRequest.ResourceSpans[0].ScopeSpans[0].Spans[0]
	if !bytes.Equal(span.TraceId, bytes.Repeat([]byte{0x11}, 16)) {
		t.Fatal("incoming W3C context was lost")
	}
	var metricRequest metricspb.ExportMetricsServiceRequest
	if err := proto.Unmarshal(payloads["/v1/metrics"][0], &metricRequest); err != nil {
		t.Fatal(err)
	}
	found := false
	for _, resource := range metricRequest.ResourceMetrics {
		for _, scope := range resource.ScopeMetrics {
			for _, m := range scope.Metrics {
				if m.Name == "togglemaster.http.requests" {
					found = true
					if len(m.GetSum().DataPoints) != 1 || m.GetSum().DataPoints[0].GetAsInt() != 1 {
						t.Fatal("request metric must count the failure once and exclude health")
					}
					for _, a := range m.GetSum().DataPoints[0].Attributes {
						if a.Key == "http_route" && a.Value.GetStringValue() != "/items/{id}" {
							t.Fatal("high-cardinality route in metrics")
						}
					}
				}
			}
		}
	}
	if !found {
		t.Fatal("application request counter missing")
	}
	var logRequest logspb.ExportLogsServiceRequest
	if err := proto.Unmarshal(payloads["/v1/logs"][0], &logRequest); err != nil {
		t.Fatal(err)
	}
	entry := logRequest.ResourceLogs[0].ScopeLogs[0].LogRecords[0]
	if !bytes.Equal(entry.TraceId, span.TraceId) {
		t.Fatal("access log and trace are not correlated")
	}
}
