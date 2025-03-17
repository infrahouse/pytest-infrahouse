output "elastic_password" {
  sensitive = true
  value     = module.elasticsearch.elastic_password
}

output "cluster_name" {
  value = local.cluster_name
}

output "elasticsearch_url" {
  value = module.elasticsearch.cluster_master_url
}

output "idle_timeout_master" {
  value = module.elasticsearch.idle_timeout_master
}

output "keypair_name" {
  value = aws_key_pair.elastic.key_name
}

output "kibana_system_password" {
  sensitive = true
  value     = module.elasticsearch.kibana_system_password
}

output "zone_id" {
  value = data.aws_route53_zone.elastic.zone_id
}
