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

output "jumphost_instance_profile_arn" {
  description = "ARN of the IAM instance profile assigned to jumphost instances"
  value       = module.jumphost.jumphost_instance_profile__arn
}

output "jumphost_instance_profile_name" {
  description = "Name of the IAM instance profile assigned to jumphost instances"
  value       = module.jumphost.jumphost_instance_profile_name
}

output "jumphost_asg_name" {
  description = "Name of the Auto Scaling Group managing jumphost instances"
  value       = module.jumphost.jumphost_asg_name
}
