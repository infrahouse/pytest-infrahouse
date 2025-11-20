output "instance_profile_arn" {
  description = "ARN of the created IAM instance profile"
  value       = module.instance_profile.instance_profile_arn
}

output "instance_profile_name" {
  description = "Name of the created IAM instance profile"
  value       = module.instance_profile.instance_profile_name
}

output "instance_role_arn" {
  description = "ARN of the IAM role associated with the instance profile"
  value       = module.instance_profile.instance_role_arn
}

output "instance_role_name" {
  description = "Name of the IAM role associated with the instance profile"
  value       = module.instance_profile.instance_role_name
}
