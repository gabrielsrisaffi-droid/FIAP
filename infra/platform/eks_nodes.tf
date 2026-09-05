resource "aws_launch_template" "eks_nodes" {
  count = var.enable_eks ? 1 : 0

  name_prefix            = "${var.eks_cluster_name}-nodes-"
  description            = "Nodes EKS do ToggleMaster no AWS Academy"
  update_default_version = true

  block_device_mappings {
    device_name = "/dev/xvda"

    ebs {
      delete_on_termination = true
      encrypted             = true
      volume_size           = 20
      volume_type           = "gp3"
    }
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
    instance_metadata_tags      = "disabled"
  }

  tags = {
    Name = "${var.eks_cluster_name}-nodes"
  }

  lifecycle {
    create_before_destroy = true
  }
}
