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