data "aws_caller_identity" "current" {}

locals {
  state_bucket_name = "${var.bucket_prefix}-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket" "terraform_state" {
  bucket = local.state_bucket_name

  lifecycle {
    prevent_destroy = true
  }
}