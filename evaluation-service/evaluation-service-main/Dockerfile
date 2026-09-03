FROM golang:1.21-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN go build -o evaluation-service .

FROM alpine:3.19

WORKDIR /app

RUN apk add --no-cache ca-certificates && update-ca-certificates

RUN apk add --no-cache ca-certificates && update-ca-certificates

RUN adduser -D appuser

COPY --from=builder /app/evaluation-service .

USER appuser

EXPOSE 8004

CMD ["./evaluation-service"]