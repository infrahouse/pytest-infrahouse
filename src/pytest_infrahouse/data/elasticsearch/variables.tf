variable "region" {}
variable "subnet_public_ids" {}
variable "bootstrap_mode" {
  type = bool
}
variable "test_zone" {}
variable "role_arn" {}
variable "environment" {
  default = "development"
}
variable "internet_gateway_id" {}
