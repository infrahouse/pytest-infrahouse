output "subnet_public_ids" {
  description = "List of public subnet IDs in the service network"
  value       = module.service-network.subnet_public_ids
}

output "subnet_private_ids" {
  description = "List of private subnet IDs in the service network"
  value       = module.service-network.subnet_private_ids
}

output "internet_gateway_id" {
  description = "Internet Gateway ID for the service network VPC"
  value       = module.service-network.internet_gateway_id
}

output "vpc_id" {
  description = "VPC ID of the created service network"
  value       = module.service-network.vpc_id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = module.service-network.vpc_cidr_block
}

output "management_cidr_block" {
  description = "CIDR block of the management VPC"
  value       = module.service-network.management_cidr_block
}

output "route_table_all_ids" {
  description = "List of IDs of all route tables in the service network"
  value       = module.service-network.route_table_all_ids
}

output "subnet_all_ids" {
  description = "List of IDs of all subnets (both public and private)"
  value       = module.service-network.subnet_all_ids
}

output "vpc_flow_bucket_name" {
  description = "S3 bucket name containing VPC Flow logs (if VPC Flow logging is enabled)"
  value       = module.service-network.vpc_flow_bucket_name
}
