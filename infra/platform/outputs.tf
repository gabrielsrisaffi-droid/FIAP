output "vpc_id" {
  description = "ID da VPC principal."
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs das sub-redes públicas."
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs das sub-redes privadas."
  value       = aws_subnet.private[*].id
}
output "ecr_repository_urls" {
  description = "URLs dos repositórios ECR dos microsserviços."

  value = {
    for service_name, repository in aws_ecr_repository.services :
    service_name => repository.repository_url
  }
}
output "sqs_queue_url" {
  description = "URL da fila usada pelos serviços evaluation e analytics."
  value       = aws_sqs_queue.events.url
}

output "sqs_queue_arn" {
  description = "ARN da fila de eventos."
  value       = aws_sqs_queue.events.arn
}

output "dynamodb_table_name" {
  description = "Nome da tabela analítica."
  value       = aws_dynamodb_table.analytics.name
}

output "dynamodb_table_arn" {
  description = "ARN da tabela analítica."
  value       = aws_dynamodb_table.analytics.arn
}
output "database_subnet_group_name" {
  description = "Grupo de sub-redes privadas usado pelos bancos RDS."
  value       = aws_db_subnet_group.databases.name
}

output "redis_subnet_group_name" {
  description = "Grupo de sub-redes privadas usado pelo ElastiCache."
  value       = aws_elasticache_subnet_group.redis.name
}

output "postgresql_security_group_id" {
  description = "Security Group dos bancos PostgreSQL."
  value       = aws_security_group.postgresql.id
}

output "redis_security_group_id" {
  description = "Security Group do Redis."
  value       = aws_security_group.redis.id
}