module "instance_profile" {
  source       = "registry.infrahouse.com/infrahouse/instance-profile/aws"
  version      = "1.9.0"
  profile_name = "website-pod-profile"
  permissions  = data.aws_iam_policy_document.permissions.json
}
