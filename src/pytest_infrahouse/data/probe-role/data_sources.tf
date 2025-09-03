data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "permissions" {
  statement {
    actions = [
      "sts:GetCallerIdentity"
    ]
    resources = [
      "*"
    ]
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

data "aws_iam_role" "caller_role" {
  name = split("/", split(":", data.aws_caller_identity.current.arn)[5])[1]
}
