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