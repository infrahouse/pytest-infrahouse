data "aws_iam_policy_document" "permissions" {
  statement {
    actions = [
      "sts:GetCallerIdentity"
    ]
    # sts:GetCallerIdentity does not support resource-level permissions
    resources = ["*"]
  }
}
