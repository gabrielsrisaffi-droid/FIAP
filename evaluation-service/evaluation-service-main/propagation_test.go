package main

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/trace"
)

func TestParallelDependenciesPreserveTraceContext(t *testing.T) {
	provider := trace.NewTracerProvider()
	otel.SetTracerProvider(provider)
	otel.SetTextMapPropagator(propagation.TraceContext{})
	ctx, span := provider.Tracer("test").Start(context.Background(), "evaluation")
	defer span.End()
	var mu sync.Mutex
	seen := map[string]string{}
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		seen[r.URL.Path] = r.Header.Get("traceparent")
		mu.Unlock()
		w.Header().Set("Content-Type", "application/json")
		if strings.HasPrefix(r.URL.Path, "/flags/") {
			_, _ = w.Write([]byte(`{"name":"demo","is_enabled":true}`))
		} else {
			_, _ = w.Write([]byte(`{"flag_name":"demo","is_enabled":true,"rules":{"type":"PERCENTAGE","value":100}}`))
		}
	}))
	defer server.Close()
	app := &App{HttpClient: &http.Client{Transport: otelhttp.NewTransport(http.DefaultTransport)}, FlagServiceURL: server.URL, TargetingServiceURL: server.URL}
	info, err := app.fetchFromServices(ctx, "demo")
	if err != nil || info.Flag == nil || info.Rule == nil {
		t.Fatalf("unexpected result: %v", err)
	}
	mu.Lock()
	defer mu.Unlock()
	if len(seen) != 2 {
		t.Fatalf("expected both dependencies, got %v", seen)
	}
	for path, header := range seen {
		if !strings.Contains(header, span.SpanContext().TraceID().String()) {
			t.Fatalf("context lost at %s: %s", path, header)
		}
	}
}

func TestCancelledRequestDoesNotCallDependencies(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	app := &App{HttpClient: http.DefaultClient, FlagServiceURL: "http://127.0.0.1:1"}
	if _, err := app.fetchFlag(ctx, "demo"); err == nil {
		t.Fatal("expected cancelled outbound request to fail")
	}
}
