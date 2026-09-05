resource "aws_db_subnet_group" "databases" {
  name       = "${local.name_prefix}-db-subnets"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${local.name_prefix}-db-subnets"
  }
}

resource "aws_elasticache_subnet_group" "redis" {
  name       = "${local.name_prefix}-redis-subnets"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_security_group" "postgresql" {
  name        = "${local.name_prefix}-postgresql-sg"
  description = "Permite PostgreSQL apenas a partir das sub-redes dos nodes EKS."
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "${local.name_prefix}-postgresql-sg"
  }
}

resource "aws_vpc_security_group_ingress_rule" "postgresql" {
  for_each = toset(var.public_subnet_cidrs)

  security_group_id = aws_security_group.postgresql.id
  description       = "PostgreSQL a partir dos nodes EKS"
  cidr_ipv4         = each.value
  from_port         = 5432
  to_port           = 5432
  ip_protocol       = "tcp"
}

resource "aws_security_group" "redis" {
  name        = "${local.name_prefix}-redis-sg"
  description = "Permite Redis apenas a partir das sub-redes dos nodes EKS."
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "${local.name_prefix}-redis-sg"
  }
}

resource "aws_vpc_security_group_ingress_rule" "redis" {
  for_each = toset(var.public_subnet_cidrs)

  security_group_id = aws_security_group.redis.id
  description       = "Redis a partir dos nodes EKS"
  cidr_ipv4         = each.value
  from_port         = 6379
  to_port           = 6379
  ip_protocol       = "tcp"
}