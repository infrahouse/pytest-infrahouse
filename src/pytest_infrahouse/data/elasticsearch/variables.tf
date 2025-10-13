variable "region" {}
variable "subnet_public_ids" {}
variable "cluster_name" {}
variable "bootstrap_mode" {
  type = bool
}
variable "test_zone_id" {}
variable "role_arn" {
  default = null
}
variable "environment" {
  default = "development"
}
variable "internet_gateway_id" {}
variable "calling_test" {}
