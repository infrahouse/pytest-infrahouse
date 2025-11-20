variable "region" {
  description = "AWS region where the Route53 subzone will be created"
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

variable "parent_zone_name" {
  description = "Name of the parent Route53 DNS zone where the subzone will be created"
  type        = string
}

variable "calling_test" {
  description = "Name of the calling test file for resource tagging and tracking"
  type        = string
}
