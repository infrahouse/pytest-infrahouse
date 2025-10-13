module "elasticsearch" {
  source  = "registry.infrahouse.com/infrahouse/elasticsearch/aws"
  version = "3.11.0"
  providers = {
    aws     = aws
    aws.dns = aws
  }
  cluster_name           = local.cluster_name
  cluster_master_count   = 3
  cluster_data_count     = 1
  environment            = var.environment
  subnet_ids             = var.subnet_public_ids
  zone_id                = var.test_zone_id
  bootstrap_mode         = var.bootstrap_mode
  internet_gateway_id    = var.internet_gateway_id
  key_pair_name          = aws_key_pair.elastic.key_name
  ubuntu_codename        = "noble"
  secret_elastic_readers = []
}
