provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Phase       = "3"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}