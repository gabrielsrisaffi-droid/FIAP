variable "aws_region" {
  description = "Região AWS utilizada pelo projeto."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Nome base usado na identificação dos recursos."
  type        = string
  default     = "togglemaster"
}

variable "environment" {
  description = "Nome do ambiente implantado."
  type        = string
  default     = "academy-lab"
}

variable "vpc_cidr" {
  description = "Bloco CIDR principal da VPC."
  type        = string
  default     = "10.30.0.0/16"
}

variable "availability_zones" {
  description = "Zonas de disponibilidade usadas pelas sub-redes."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]

  validation {
    condition     = length(var.availability_zones) == 2
    error_message = "Devem ser informadas exatamente duas zonas de disponibilidade."
  }
}

variable "public_subnet_cidrs" {
  description = "Blocos CIDR das sub-redes públicas."
  type        = list(string)
  default     = ["10.30.1.0/24", "10.30.2.0/24"]

  validation {
    condition     = length(var.public_subnet_cidrs) == 2
    error_message = "Devem ser informados exatamente dois CIDRs públicos."
  }
}

variable "private_subnet_cidrs" {
  description = "Blocos CIDR das sub-redes privadas."
  type        = list(string)
  default     = ["10.30.11.0/24", "10.30.12.0/24"]

  validation {
    condition     = length(var.private_subnet_cidrs) == 2
    error_message = "Devem ser informados exatamente dois CIDRs privados."
  }
}
variable "enable_rds" {
  description = "Controla a criação dos três bancos RDS PostgreSQL."
  type        = bool
  default     = false
}

variable "postgres_engine_version" {
  description = "Versão principal do PostgreSQL."
  type        = string
  default     = "16"
}

variable "db_instance_class" {
  description = "Classe das instâncias RDS."
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "Armazenamento em GiB de cada instância RDS."
  type        = number
  default     = 20

  validation {
    condition     = var.db_allocated_storage >= 20
    error_message = "O armazenamento de cada RDS deve ter pelo menos 20 GiB."
  }
}

variable "db_master_username" {
  description = "Usuário administrador dos bancos PostgreSQL."
  type        = string
  default     = "toggleadmin"
}
variable "enable_redis" {
  description = "Controla a criação do ElastiCache Redis."
  type        = bool
  default     = false
}

variable "redis_engine_version" {
  description = "Versão do Redis usada pelo ElastiCache."
  type        = string
  default     = "7.1"
}

variable "redis_node_type" {
  description = "Classe de capacidade do Redis."
  type        = string
  default     = "cache.t3.micro"
}