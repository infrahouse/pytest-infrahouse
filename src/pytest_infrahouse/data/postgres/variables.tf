variable "region" {
  description = "AWS region where the PostgreSQL RDS instance will be deployed"
  type        = string
  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]+$", var.region))
    error_message = "Region must be a valid AWS region (e.g., us-east-1, eu-west-2)."
  }
}

variable "subnet_private_ids" {
  description = <<-EOT
    List of private subnet IDs for the RDS subnet group.
    RDS requires at least two subnets in different availability zones.
  EOT
  type        = list(string)
  validation {
    condition     = length(var.subnet_private_ids) >= 2
    error_message = "RDS requires at least 2 subnets in different availability zones."
  }
}

variable "role_arn" {
  description = "Optional IAM role ARN to assume for resource creation. Used for cross-account testing."
  type        = string
  default     = null
  validation {
    condition     = var.role_arn == null || can(regex("^arn:aws:iam::[0-9]{12}:role/", var.role_arn))
    error_message = "role_arn must be a valid IAM role ARN or null."
  }
}

variable "environment" {
  description = "Environment name for resource naming and tagging"
  type        = string
  default     = "test"
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.environment))
    error_message = "Environment must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "calling_test" {
  description = "Name of the calling test file for resource tagging and tracking"
  type        = string
}

variable "db_identifier" {
  description = <<-EOT
    The RDS instance identifier. Must be unique within AWS account and region.
    Will be used as prefix for related resources.
  EOT
  type        = string
  default     = "pytest-postgres"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]+$", var.db_identifier))
    error_message = "DB identifier must start with a letter and contain only lowercase letters, numbers, and hyphens."
  }
}

variable "postgres_version" {
  description = <<-EOT
    PostgreSQL engine version. Check AWS RDS documentation for available versions.
    Default is latest stable LTS version.
  EOT
  type        = string
  default     = "16.6"
  validation {
    condition     = can(regex("^[0-9]+\\.[0-9]+$", var.postgres_version))
    error_message = "PostgreSQL version must be in format X.Y (e.g., 16.6)."
  }
}

variable "instance_class" {
  description = <<-EOT
    RDS instance type. Default is smallest available for cost optimization in testing.
    See: https://aws.amazon.com/rds/instance-types/
  EOT
  type        = string
  default     = "db.t3.micro"
  validation {
    condition     = can(regex("^db\\.[a-z0-9]+\\.[a-z0-9]+$", var.instance_class))
    error_message = "Instance class must be a valid RDS instance type (e.g., db.t3.micro)."
  }
}

variable "allocated_storage" {
  description = "Initial storage allocation in GB. Minimum is 20 for gp3 storage type."
  type        = number
  default     = 20
  validation {
    condition     = var.allocated_storage >= 20 && var.allocated_storage <= 65536
    error_message = "Allocated storage must be between 20 and 65536 GB."
  }
}

variable "max_allocated_storage" {
  description = <<-EOT
    Maximum storage limit in GB for autoscaling. Set to 0 to disable autoscaling.
    Must be greater than allocated_storage if enabled.
  EOT
  type        = number
  default     = 100
  validation {
    condition     = var.max_allocated_storage == 0 || var.max_allocated_storage >= 20
    error_message = "Max allocated storage must be 0 (disabled) or at least 20 GB."
  }
}

variable "database_name" {
  description = "Name of the default database to create"
  type        = string
  default     = "testdb"
  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9_]*$", var.database_name))
    error_message = "Database name must start with a letter and contain only letters, numbers, and underscores."
  }
}

variable "master_username" {
  description = "Master username for the database"
  type        = string
  default     = "pytest_admin"
  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9_]*$", var.master_username)) && var.master_username != "postgres"
    error_message = "Username must start with a letter, contain only alphanumeric characters and underscores, and cannot be 'postgres'."
  }
}

variable "backup_retention_period" {
  description = "Number of days to retain automated backups. 0 disables automated backups."
  type        = number
  default     = 1
  validation {
    condition     = var.backup_retention_period >= 0 && var.backup_retention_period <= 35
    error_message = "Backup retention period must be between 0 and 35 days."
  }
}

variable "enable_performance_insights" {
  description = "Enable Performance Insights for query performance monitoring"
  type        = bool
  default     = true
}

variable "enable_enhanced_monitoring" {
  description = "Enable Enhanced Monitoring for detailed OS metrics"
  type        = bool
  default     = true
}

variable "enabled_cloudwatch_logs_exports" {
  description = <<-EOT
    List of log types to export to CloudWatch.
    Valid values: postgresql, upgrade
  EOT
  type        = list(string)
  default     = ["postgresql", "upgrade"]
  validation {
    condition     = alltrue([for log in var.enabled_cloudwatch_logs_exports : contains(["postgresql", "upgrade"], log)])
    error_message = "CloudWatch log exports must be 'postgresql' or 'upgrade'."
  }
}