data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "permissions" {
  statement {
    actions = [
      "sts:GetCallerIdentity"
    ]
    # sts:GetCallerIdentity does not support resource-level permissions
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type = "AWS"
      identifiers = concat(
        var.trusted_arns,
        [
          data.aws_iam_role.caller_role.arn
        ]
      )
    }
  }
}

# Parse the caller's role name from assumed-role ARN
# Example ARN: arn:aws:sts::123456789012:assumed-role/RoleName/SessionName
# We extract "RoleName" from the ARN by:
# 1. Splitting by ":" and taking element [5] -> "assumed-role/RoleName/SessionName"
# 2. Splitting by "/" and taking element [1] -> "RoleName"
data "aws_iam_role" "caller_role" {
  name = split("/", split(":", data.aws_caller_identity.current.arn)[5])[1]
}
