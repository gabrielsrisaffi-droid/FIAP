FROM golang:1.26-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN go build -o auth-service .

FROM alpine:3.22

WORKDIR /app

RUN adduser -D appuser

COPY --from=builder /app/auth-service .

USER appuser

EXPOSE 8001

CMD ["./auth-service"]
