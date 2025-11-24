# Connection information
output "endpoint" {
  description = "Full connection endpoint for the PostgreSQL instance (host:port)"
  value       = aws_db_instance.postgres.endpoint
}

output "address" {
  description = "The hostname of the RDS instance"
  value       = aws_db_instance.postgres.address
}

output "port" {
  description = "The database port"
  value       = aws_db_instance.postgres.port
}

output "database_name" {
  description = "The name of the default database"
  value       = aws_db_instance.postgres.db_name
}

# Authentication
output "master_username" {
  description = "The master username for database access"
  value       = aws_db_instance.postgres.username
}

output "master_password" {
  description = "The master password for database access"
  value       = random_password.postgres_password.result
  sensitive   = true
}

output "secret_arn" {
  description = "ARN of the Secrets Manager secret containing connection details"
  value       = aws_secretsmanager_secret.postgres_password.arn
}

output "secret_name" {
  description = "Name of the Secrets Manager secret containing connection details"
  value       = aws_secretsmanager_secret.postgres_password.name
}

# Instance information
output "instance_id" {
  description = "The RDS resource ID (internal AWS identifier)"
  value       = aws_db_instance.postgres.id
}

output "instance_identifier" {
  description = "The RDS instance identifier (user-defined name)"
  value       = aws_db_instance.postgres.identifier
}

output "instance_arn" {
  description = "The ARN of the RDS instance"
  value       = aws_db_instance.postgres.arn
}

output "instance_class" {
  description = "The instance type of the RDS instance"
  value       = aws_db_instance.postgres.instance_class
}

output "engine_version" {
  description = "The PostgreSQL engine version"
  value       = aws_db_instance.postgres.engine_version_actual
}

# Network configuration
output "security_group_id" {
  description = "ID of the security group attached to the RDS instance"
  value       = aws_security_group.postgres.id
}

output "db_subnet_group_name" {
  description = "Name of the DB subnet group"
  value       = aws_db_subnet_group.postgres.name
}

output "availability_zone" {
  description = "The availability zone where the RDS instance is deployed"
  value       = aws_db_instance.postgres.availability_zone
}

# Storage configuration
output "allocated_storage" {
  description = "The allocated storage size in GB"
  value       = aws_db_instance.postgres.allocated_storage
}

output "storage_encrypted" {
  description = "Whether the storage is encrypted"
  value       = aws_db_instance.postgres.storage_encrypted
}

output "kms_key_id" {
  description = "The KMS key ID used for encryption"
  value       = aws_db_instance.postgres.kms_key_id
}

# Monitoring
output "enhanced_monitoring_role_arn" {
  description = "The ARN of the enhanced monitoring IAM role"
  value       = var.enable_enhanced_monitoring ? aws_iam_role.rds_enhanced_monitoring[0].arn : null
}

output "performance_insights_enabled" {
  description = "Whether Performance Insights is enabled"
  value       = aws_db_instance.postgres.performance_insights_enabled
}

output "performance_insights_kms_key" {
  description = "The KMS key ID used for Performance Insights data encryption"
  value       = aws_db_instance.postgres.performance_insights_kms_key_id
}

output "cloudwatch_log_exports" {
  description = "List of log types being exported to CloudWatch"
  value       = aws_db_instance.postgres.enabled_cloudwatch_logs_exports
}

# Connection strings
output "connection_string" {
  description = <<-EOT
    PostgreSQL connection string for applications.
    Format: postgresql://username:password@host:port/database
  EOT
  value       = "postgresql://${aws_db_instance.postgres.username}:${random_password.postgres_password.result}@${aws_db_instance.postgres.address}:${aws_db_instance.postgres.port}/${aws_db_instance.postgres.db_name}"
  sensitive   = true
}

output "jdbc_connection_string" {
  description = <<-EOT
    JDBC connection string for Java applications.
    Format: jdbc:postgresql://host:port/database
  EOT
  value       = "jdbc:postgresql://${aws_db_instance.postgres.address}:${aws_db_instance.postgres.port}/${aws_db_instance.postgres.db_name}"
}

# Tags
output "tags" {
  description = "Tags applied to the RDS instance"
  value       = aws_db_instance.postgres.tags_all
}