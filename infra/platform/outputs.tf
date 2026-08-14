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