locals {
  # S3 bucket replicas (access logs, snapshots) must live outside the test region.
  replication_region = var.region == "us-east-1" ? "us-west-1" : "us-east-1"
}

module "elasticsearch" {
  source  = "registry.infrahouse.com/infrahouse/elasticsearch/aws"
  version = "5.1.1"
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
  key_pair_name          = aws_key_pair.elastic.key_name
  ubuntu_codename        = var.ubuntu_codename
  secret_elastic_readers = []
  replication_region     = local.replication_region
  # Test buckets must not block terraform destroy even when non-empty.
  snapshot_force_destroy       = true
  alb_access_log_force_destroy = true
  alarm_emails = [
    "test@example.com"
  ]
}
