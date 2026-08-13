output "state_bucket_name" {
  description = "Nome do bucket usado pelo backend remoto."
  value       = aws_s3_bucket.terraform_state.id
}

output "state_bucket_arn" {
  description = "ARN do bucket do state."
  value       = aws_s3_bucket.terraform_state.arn
}