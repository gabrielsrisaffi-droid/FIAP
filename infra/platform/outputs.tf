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
output "rds_endpoints" {
  description = "Endpoints privados dos bancos PostgreSQL."

  value = {
    for service_name, database in aws_db_instance.postgresql :
    service_name => database.address
  }
}

output "rds_database_names" {
  description = "Nomes dos bancos PostgreSQL."

  value = {
    for service_name, database in aws_db_instance.postgresql :
    service_name => database.db_name
  }
}

output "rds_master_username" {
  description = "Usuário administrador dos bancos."
  value       = var.db_master_username
}

output "rds_master_passwords" {
  description = "Senhas geradas para os bancos PostgreSQL."

  value = {
    for service_name, password in random_password.database :
    service_name => password.result
  }

  sensitive = true
}
output "redis_primary_endpoint" {
  description = "Endpoint privado do Redis."
  value       = try(aws_elasticache_replication_group.redis[0].primary_endpoint_address, null)
}

output "redis_port" {
  description = "Porta de conexão do Redis."
  value       = try(aws_elasticache_replication_group.redis[0].port, null)
}

output "redis_url" {
  description = "URL TLS usada pelo evaluation-service."

  value = var.enable_redis ? format(
    "rediss://%s:%s",
    aws_elasticache_replication_group.redis[0].primary_endpoint_address,
    aws_elasticache_replication_group.redis[0].port
  ) : null
}
output "eks_cluster_name" {
  description = "Nome do cluster EKS."
  value       = try(aws_eks_cluster.main[0].name, null)
}

output "eks_cluster_endpoint" {
  description = "Endpoint da API do Kubernetes."
  value       = try(aws_eks_cluster.main[0].endpoint, null)
}

output "eks_cluster_security_group_id" {
  description = "Security Group criado pelo EKS para o cluster."
  value       = try(aws_eks_cluster.main[0].vpc_config[0].cluster_security_group_id, null)
}

output "eks_node_group_name" {
  description = "Nome do node group gerenciado."
  value       = try(aws_eks_node_group.main[0].node_group_name, null)
}