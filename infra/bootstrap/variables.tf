variable "aws_region" {
  description = "Região utilizada no AWS Academy."
  type        = string
  default     = "us-east-1"
}

variable "bucket_prefix" {
  description = "Prefixo do bucket que armazenará o state do Terraform."
  type        = string
  default     = "togglemaster-fase3-tfstate"
}