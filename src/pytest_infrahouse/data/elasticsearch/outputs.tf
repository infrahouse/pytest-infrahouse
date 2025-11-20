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
