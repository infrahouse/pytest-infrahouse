module "elasticsearch" {
  source  = "registry.infrahouse.com/infrahouse/elasticsearch/aws"
  version = "3.12.0"
  providers = {
    aws     = aws
    aws.dns = aws
  }
  cluster_name = var.cluster_name
  # 3 master nodes required for quorum (majority consensus)
  cluster_master_count = 3
  # Single data node sufficient for test fixture - no redundancy needed
  cluster_data_count     = 1
  environment            = var.environment
  subnet_ids             = var.subnet_public_ids
  zone_id                = var.test_zone_id
  bootstrap_mode         = var.bootstrap_mode
  internet_gateway_id    = var.internet_gateway_id
  key_pair_name          = aws_key_pair.elastic.key_name
  ubuntu_codename        = var.ubuntu_codename
  secret_elastic_readers = []
}
