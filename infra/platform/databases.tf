resource "random_password" "database" {
  for_each = var.enable_rds ? local.databases : {}

  length      = 24
  min_lower   = 2
  min_upper   = 2
  min_numeric = 2
  special     = false
}

resource "aws_db_instance" "postgresql" {
  for_each = var.enable_rds ? local.databases : {}

  identifier = each.value.identifier
  db_name    = each.value.database_name

  engine         = "postgres"
  engine_version = var.postgres_engine_version
  instance_class = var.db_instance_class

  username = var.db_master_username
  password = random_password.database[each.key].result
  port     = 5432

  allocated_storage = var.db_allocated_storage
  storage_type      = "gp3"
  storage_encrypted = true

  db_subnet_group_name   = aws_db_subnet_group.databases.name
  vpc_security_group_ids = [aws_security_group.postgresql.id]
  publicly_accessible    = false
  multi_az               = false

  backup_retention_period = 1
  copy_tags_to_snapshot   = true

  auto_minor_version_upgrade   = true
  apply_immediately            = true
  performance_insights_enabled = false

  deletion_protection      = false
  skip_final_snapshot      = true
  delete_automated_backups = true

  tags = {
    Name     = each.value.identifier
    Database = each.value.database_name
    Service  = "${each.key}-service"
  }
}