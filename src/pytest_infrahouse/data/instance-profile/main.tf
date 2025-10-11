resource "random_string" "suffix" {
  length  = 6
  special = false
}

module "instance_profile" {
  source       = "registry.infrahouse.com/infrahouse/instance-profile/aws"
  version      = "1.9.0"
  profile_name = "website-pod-profile-${random_string.suffix.result}"
  permissions  = data.aws_iam_policy_document.permissions.json
}
