provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "ToggleMaster"
      Phase       = "3"
      Environment = "academy-lab"
      ManagedBy   = "Terraform"
    }
  }
}