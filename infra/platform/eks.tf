data "aws_iam_role" "academy_lab" {
  name = "LabRole"
}

locals {
  eks_cluster_role_arn = data.aws_iam_role.academy_lab.arn
  eks_node_role_arn    = data.aws_iam_role.academy_lab.arn
}

resource "aws_eks_cluster" "main" {
  count = var.enable_eks ? 1 : 0

  name     = var.eks_cluster_name
  role_arn = local.eks_cluster_role_arn
  version  = var.kubernetes_version

  access_config {
    authentication_mode                         = "API_AND_CONFIG_MAP"
    bootstrap_cluster_creator_admin_permissions = true
  }

  vpc_config {
    subnet_ids = concat(
      aws_subnet.public[*].id,
      aws_subnet.private[*].id
    )

    endpoint_public_access  = true
    endpoint_private_access = true
    public_access_cidrs     = var.eks_public_access_cidrs
  }

  enabled_cluster_log_types = [
    "api",
    "audit",
    "authenticator",
  ]

  tags = {
    Name = var.eks_cluster_name
  }
}

resource "aws_eks_node_group" "main" {
  count = var.enable_eks ? 1 : 0

  cluster_name    = aws_eks_cluster.main[0].name
  node_group_name = "${var.eks_cluster_name}-nodes"
  node_role_arn   = local.eks_node_role_arn
  subnet_ids      = aws_subnet.public[*].id

  ami_type       = "AL2023_x86_64_STANDARD"
  capacity_type  = "ON_DEMAND"
  instance_types = var.eks_node_instance_types
  disk_size      = 20

  scaling_config {
    desired_size = var.eks_node_desired_size
    min_size     = var.eks_node_min_size
    max_size     = var.eks_node_max_size
  }

  update_config {
    max_unavailable = 1
  }

  labels = {
    workload = "togglemaster"
  }

  tags = {
    Name = "${var.eks_cluster_name}-nodes"
  }

  depends_on = [aws_eks_cluster.main]
}