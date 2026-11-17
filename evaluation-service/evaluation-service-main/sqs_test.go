package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/credentials"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/sqs"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/trace"
)

func TestSQSMessageCarriesEvaluationTrace(t *testing.T) {
	provider := trace.NewTracerProvider()
	otel.SetTracerProvider(provider)
	otel.SetTextMapPropagator(propagation.TraceContext{})
	ctx, span := provider.Tracer("test").Start(context.Background(), "evaluation")
	defer span.End()
	var input sqs.SendMessageInput
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
			t.Errorf("decode SQS request: %v", err)
		}
		w.Header().Set("Content-Type", "application/x-amz-json-1.0")
		_, _ = w.Write([]byte(`{"MessageId":"test-message"}`))
	}))
	defer server.Close()
	sess, err := session.NewSession(&aws.Config{Region: aws.String("us-east-1"), Endpoint: aws.String(server.URL),
		Credentials: credentials.NewStaticCredentials("test", "test", ""), MaxRetries: aws.Int(0)})
	if err != nil {
		t.Fatal(err)
	}
	app := &App{SqsSvc: sqs.New(sess), SqsQueueURL: server.URL + "/queue"}
	app.sendEvaluationEvent(ctx, "synthetic-user", "demo", true)
	attribute := input.MessageAttributes["traceparent"]
	if attribute == nil || !strings.Contains(aws.StringValue(attribute.StringValue), span.SpanContext().TraceID().String()) {
		t.Fatalf("trace context missing from SQS attributes: %v", input.MessageAttributes)
	}
	var event EvaluationEvent
	if err := json.Unmarshal([]byte(aws.StringValue(input.MessageBody)), &event); err != nil || event.FlagName != "demo" || !event.Result {
		t.Fatalf("original event contract changed: %v", err)
	}
}
