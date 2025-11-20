output "elastic_password" {
  description = "Password for the elastic superuser account"
  sensitive   = true
  value       = module.elasticsearch.elastic_password
}

output "cluster_name" {
  description = "Name of the Elasticsearch cluster"
  value       = var.cluster_name
}

output "elasticsearch_url" {
  description = "URL of the Elasticsearch cluster master node"
  value       = module.elasticsearch.cluster_master_url
}

output "idle_timeout_master" {
  description = "Idle timeout value for the master node load balancer"
  value       = module.elasticsearch.idle_timeout_master
}

output "keypair_name" {
  description = "Name of the EC2 key pair used for Elasticsearch instances"
  value       = aws_key_pair.elastic.key_name
}

output "kibana_system_password" {
  description = "Password for the Kibana system account"
  sensitive   = true
  value       = module.elasticsearch.kibana_system_password
}

output "zone_id" {
  description = "Route53 hosted zone ID where Elasticsearch DNS records are created"
  value       = var.test_zone_id
}

output "subnet_ids" {
  description = "List of subnet IDs where Elasticsearch nodes are deployed"
  value       = var.subnet_public_ids
}

output "master_load_balancer_arn" {
  description = "ARN of the load balancer for master nodes"
  value       = module.elasticsearch.cluster_master_load_balancer_arn
}

output "master_target_group_arn" {
  description = "ARN of the target group for master nodes"
  value       = module.elasticsearch.cluster_master_target_group_arn
}

output "data_load_balancer_arn" {
  description = "ARN of the load balancer for data nodes (null in bootstrap mode)"
  value       = module.elasticsearch.cluster_data_load_balancer_arn
}

output "data_target_group_arn" {
  description = "ARN of the target group for data nodes (null in bootstrap mode)"
  value       = module.elasticsearch.cluster_data_target_group_arn
}

output "snapshots_bucket" {
  description = "S3 bucket name used for Elasticsearch snapshots"
  value       = module.elasticsearch.snapshots_bucket
}

output "master_instance_role_arn" {
  description = "ARN of the IAM role attached to master node instances"
  value       = module.elasticsearch.master_instance_role_arn
}

output "data_instance_role_arn" {
  description = "ARN of the IAM role attached to data node instances"
  value       = module.elasticsearch.data_instance_role_arn
}
