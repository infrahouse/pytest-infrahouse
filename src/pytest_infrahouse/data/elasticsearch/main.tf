module "elasticsearch" {
  source  = "registry.infrahouse.com/infrahouse/elasticsearch/aws"
  version = "~> 3.1, >= 3.1.2"
  providers = {
    aws     = aws
    aws.dns = aws
  }
  cluster_name         = local.cluster_name
  cluster_master_count = 3
  cluster_data_count   = 1
  environment          = var.environment
  subnet_ids           = var.subnet_public_ids
  zone_id              = data.aws_route53_zone.elastic.zone_id
  bootstrap_mode       = var.bootstrap_mode
  internet_gateway_id  = var.internet_gateway_id
  key_pair_name        = aws_key_pair.elastic.key_name
}
