package main

import (
	"context"
	"errors"
	"io"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlplog/otlploghttp"
	"go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetrichttp"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	logapi "go.opentelemetry.io/otel/log"
	"go.opentelemetry.io/otel/log/global"
	"go.opentelemetry.io/otel/metric"
	"go.opentelemetry.io/otel/propagation"
	logsdk "go.opentelemetry.io/otel/sdk/log"
	metricsdk "go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/resource"
	tracesdk "go.opentelemetry.io/otel/sdk/trace"
)

// Services have independent Docker build contexts. Keep this file and its tests
// identical in auth-service and evaluation-service.
func setupTelemetry(service string) (func(context.Context) error, error) {
	var shutdowns []func(context.Context) error
	shutdown := func(ctx context.Context) error {
		var errs []error
		for _, stop := range shutdowns {
			errs = append(errs, stop(ctx))
		}
		return errors.Join(errs...)
	}
	// Existing Phase 3 environments remain usable without a collector.
	if os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT") == "" || os.Getenv("OTEL_SDK_DISABLED") == "true" {
		return shutdown, nil
	}
	ctx := context.Background()
	res, err := resource.New(ctx, resource.WithFromEnv(), resource.WithAttributes(attribute.String("service.name", service)))
	if err != nil {
		return shutdown, err
	}
	traceExporter, err := otlptracehttp.New(ctx)
	if err != nil {
		return shutdown, err
	}
	tp := tracesdk.NewTracerProvider(tracesdk.WithResource(res), tracesdk.WithBatcher(traceExporter))
	shutdowns = append(shutdowns, tp.Shutdown)
	metricExporter, err := otlpmetrichttp.New(ctx)
	if err != nil {
		return shutdown, err
	}
	mp := metricsdk.NewMeterProvider(metricsdk.WithResource(res), metricsdk.WithReader(metricsdk.NewPeriodicReader(metricExporter)))
	shutdowns = append(shutdowns, mp.Shutdown)
	logExporter, err := otlploghttp.New(ctx)
	if err != nil {
		return shutdown, err
	}
	lp := logsdk.NewLoggerProvider(logsdk.WithResource(res), logsdk.WithProcessor(logsdk.NewBatchProcessor(logExporter)))
	shutdowns = append(shutdowns, lp.Shutdown)
	otel.SetTracerProvider(tp)
	otel.SetMeterProvider(mp)
	global.SetLoggerProvider(lp)
	otel.SetTextMapPropagator(propagation.TraceContext{})
	log.SetOutput(io.MultiWriter(os.Stdout, telemetryLogWriter{}))
	return shutdown, nil
}

type telemetryLogWriter struct{}

func (telemetryLogWriter) Write(p []byte) (int, error) {
	var record logapi.Record
	record.SetTimestamp(time.Now())
	record.SetSeverity(logapi.SeverityInfo)
	record.SetBody(attribute.StringValue(strings.TrimSpace(string(p))))
	global.Logger("togglemaster.application").Emit(context.Background(), record)
	return len(p), nil
}

type statusWriter struct {
	http.ResponseWriter
	status int
}

func (w *statusWriter) Unwrap() http.ResponseWriter { return w.ResponseWriter }
func (w *statusWriter) WriteHeader(code int) {
	if w.status == 0 {
		w.status = code
		w.ResponseWriter.WriteHeader(code)
	}
}
func (w *statusWriter) Write(b []byte) (int, error) {
	if w.status == 0 {
		w.WriteHeader(http.StatusOK)
	}
	return w.ResponseWriter.Write(b)
}

// Route is a fixed template, never a query string, API key or user identifier.
func instrumentHandler(service, route string, next http.Handler) http.Handler {
	if route == "/health" {
		return next
	}
	meter := otel.Meter("togglemaster.http")
	requests, err := meter.Int64Counter("togglemaster.http.requests")
	if err != nil {
		panic(err)
	}
	duration, err := meter.Float64Histogram("togglemaster.http.duration", metric.WithUnit("s"),
		metric.WithExplicitBucketBoundaries(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10))
	if err != nil {
		panic(err)
	}
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		writer := &statusWriter{ResponseWriter: w}
		next.ServeHTTP(writer, r)
		status := writer.status
		if status == 0 {
			status = http.StatusOK
		}
		attrs := metric.WithAttributes(attribute.String("http_route", route),
			attribute.String("http_request_method", r.Method), attribute.Int("http_response_status_code", status))
		requests.Add(r.Context(), 1, attrs)
		duration.Record(r.Context(), time.Since(start).Seconds(), attrs)
		var record logapi.Record
		record.SetTimestamp(time.Now())
		record.SetSeverity(logapi.SeverityInfo)
		if status >= 500 {
			record.SetSeverity(logapi.SeverityError)
		}
		record.SetBody(attribute.StringValue("HTTP request completed"))
		record.AddAttributes(attribute.String("service.name", service), attribute.String("http.route", route), attribute.String("http.request.method", r.Method), attribute.Int("http.response.status_code", status))
		global.Logger("togglemaster.http").Emit(r.Context(), record)
	})
	return otelhttp.NewHandler(handler, route)
}

func serveHTTP(port string, handler http.Handler) error {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	server := &http.Server{Addr: ":" + port, Handler: handler, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 15 * time.Second, WriteTimeout: 20 * time.Second, IdleTimeout: 60 * time.Second}
	done := make(chan error, 1)
	go func() { done <- server.ListenAndServe() }()
	select {
	case err := <-done:
		if errors.Is(err, http.ErrServerClosed) {
			return nil
		}
		return err
	case <-ctx.Done():
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		return server.Shutdown(shutdownCtx)
	}
}

func flushTelemetry(shutdown func(context.Context) error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := shutdown(ctx); err != nil {
		log.Printf("Falha ao finalizar telemetria: %v", err)
	}
}
