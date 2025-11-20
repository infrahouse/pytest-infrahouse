output "role_name" {
  description = "Name of the created probe IAM role"
  value       = aws_iam_role.probe.name
}

output "role_arn" {
  description = "ARN of the created probe IAM role for assumption in tests"
  value       = aws_iam_role.probe.arn
}
