resource "random_string" "suffix" {
  length  = 8
  special = false
}

module "jumphost" {
  source             = "registry.infrahouse.com/infrahouse/jumphost/aws"
  version            = "4.3.0"
  environment        = var.environment
  keypair_name       = aws_key_pair.jumphost.key_name
  efs_creation_token = "jumphost-home-${random_string.suffix.result}"
  route53_zone_id    = var.test_zone_id
  subnet_ids         = var.subnet_private_ids
  nlb_subnet_ids     = var.subnet_public_ids
  # Single instance is sufficient for test fixture - provides access to test resources
  asg_min_size             = 1
  asg_max_size             = 1
  puppet_hiera_config_path = "/opt/infrahouse-puppet-data/environments/${var.environment}/hiera.yaml"
  packages = [
    "infrahouse-puppet-data"
  ]
}
