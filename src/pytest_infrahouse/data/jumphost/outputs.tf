output "jumphost_role_arn" {
  description = "ARN of the IAM role assigned to the jumphost EC2 instances"
  value       = module.jumphost.jumphost_role_arn
}

output "jumphost_role_name" {
  description = "Name of the IAM role assigned to the jumphost EC2 instances"
  value       = module.jumphost.jumphost_role_name
}

output "jumphost_hostname" {
  description = "DNS hostname for accessing the jumphost via the Network Load Balancer"
  value       = module.jumphost.jumphost_hostname
}
