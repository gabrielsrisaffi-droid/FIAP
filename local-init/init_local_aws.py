# -*- coding: utf-8 -*-

import time
import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
SQS_ENDPOINT = "http://localstack:4566"
DYNAMODB_ENDPOINT = "http://dynamodb-local:8000"
QUEUE_NAME = "togglemaster-events"
TABLE_NAME = "ToggleMasterAnalytics"

def wait_for_service(client_call, service_name, retries=30, delay=2):
    for attempt in range(1, retries + 1):
        try:
            client_call()
            print(f"{service_name} disponivel.")
            return
        except Exception as exc:
            print(f"Aguardando {service_name}... tentativa {attempt}/{retries}: {exc}")
            time.sleep(delay)
    raise RuntimeError(f"{service_name} nao ficou disponivel a tempo.")

sqs = boto3.client(
    "sqs",
    region_name=REGION,
    endpoint_url=SQS_ENDPOINT,
    aws_access_key_id="local",
    aws_secret_access_key="local",
)

dynamodb = boto3.client(
    "dynamodb",
    region_name=REGION,
    endpoint_url=DYNAMODB_ENDPOINT,
    aws_access_key_id="local",
    aws_secret_access_key="local",
)

wait_for_service(lambda: sqs.list_queues(), "LocalStack/SQS")
wait_for_service(lambda: dynamodb.list_tables(), "DynamoDB Local")

queue_response = sqs.create_queue(QueueName=QUEUE_NAME)
print(f"Fila SQS pronta: {queue_response['QueueUrl']}")

try:
    dynamodb.create_table(
        TableName=TABLE_NAME,
        AttributeDefinitions=[
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "timestamp", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "user_id", "KeyType": "HASH"},
            {"AttributeName": "timestamp", "KeyType": "RANGE"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    print(f"Tabela DynamoDB criada: {TABLE_NAME}")

    waiter = dynamodb.get_waiter("table_exists")
    waiter.wait(TableName=TABLE_NAME)
    print(f"Tabela DynamoDB disponivel: {TABLE_NAME}")

except ClientError as exc:
    if exc.response["Error"]["Code"] == "ResourceInUseException":
        print(f"Tabela DynamoDB ja existe: {TABLE_NAME}")
    else:
        raise

print("Inicializacao local concluida com sucesso.")
