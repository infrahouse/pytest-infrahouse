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
