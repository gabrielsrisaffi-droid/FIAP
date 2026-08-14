locals {
  name_prefix = "${var.project_name}-${var.environment}"

  service_names = toset([
    "analytics-service",
    "auth-service",
    "evaluation-service",
    "flag-service",
    "targeting-service",
  ])
}