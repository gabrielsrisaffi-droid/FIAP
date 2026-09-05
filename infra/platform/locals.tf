locals {
  name_prefix = "${var.project_name}-${var.environment}"

  service_names = toset([
    "analytics-service",
    "auth-service",
    "evaluation-service",
    "flag-service",
    "targeting-service",
  ])

  databases = {
    auth = {
      identifier    = "${var.project_name}-auth-db"
      database_name = "auth_db"
    }
    flag = {
      identifier    = "${var.project_name}-flag-db"
      database_name = "flags_db"
    }
    targeting = {
      identifier    = "${var.project_name}-targeting-db"
      database_name = "targeting_db"
    }
  }
}