variable "region" {
  description = "AWS region where the jumphost will be deployed"
  type        = string
  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]+$", var.region))
    error_message = "Region must be a valid AWS region (e.g., us-east-1, eu-west-2)."
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
  default     = "development"
}

variable "subnet_public_ids" {
  description = "List of public subnet IDs where the jumphost NLB will be deployed"
  type        = list(string)
}

variable "subnet_private_ids" {
  description = "List of private subnet IDs where the jumphost EC2 instances will be deployed"
  type        = list(string)
}

variable "test_zone_id" {
  description = "Route53 hosted zone ID for creating the jumphost DNS record"
  type        = string
}

variable "calling_test" {
  description = "Name of the calling test file for resource tagging and tracking"
  type        = string
}
