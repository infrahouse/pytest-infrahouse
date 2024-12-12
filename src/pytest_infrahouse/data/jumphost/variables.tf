variable "region" {
}
variable "role_arn" {
  default = null
}

variable "environment" {
  default = "development"
}

variable "subnet_public_ids" {}
variable "subnet_private_ids" {}
variable "test_zone" {}
