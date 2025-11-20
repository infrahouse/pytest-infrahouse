variable "region" {
  description = "AWS region where the Elasticsearch cluster will be deployed"
  type        = string
  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]+$", var.region))
    error_message = "Region must be a valid AWS region (e.g., us-east-1, eu-west-2)."
  }
}

variable "subnet_public_ids" {
  description = "List of public subnet IDs where Elasticsearch nodes will be deployed"
  type        = list(string)
}

variable "cluster_name" {
  description = "Name of the Elasticsearch cluster"
  type        = string
}

variable "bootstrap_mode" {
  description = "Whether to run in bootstrap mode for initial cluster setup. Requires two terraform applies."
  type        = bool
}

variable "test_zone_id" {
  description = "Route53 hosted zone ID for creating Elasticsearch DNS records"
  type        = string
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

variable "internet_gateway_id" {
  description = "Internet Gateway ID for Elasticsearch cluster internet access"
  type        = string
}

variable "calling_test" {
  description = "Name of the calling test file for resource tagging and tracking"
  type        = string
}

variable "ubuntu_codename" {
  description = "Ubuntu LTS codename for Elasticsearch instances. Only current LTS versions are supported."
  type        = string
  default     = "noble"
  validation {
    condition     = contains(["noble"], var.ubuntu_codename)
    error_message = "Only Ubuntu LTS 'noble' (24.04) is currently supported."
  }
}
