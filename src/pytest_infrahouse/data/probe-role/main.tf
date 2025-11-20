resource "aws_iam_role" "probe" {
  name_prefix        = "pytest-probe-"
  assume_role_policy = data.aws_iam_policy_document.trust.json

  tags = {
    Name = "pytest-probe-role"
  }
}

resource "aws_iam_role_policy" "probe" {
  name_prefix = "pytest-probe-policy-"
  policy      = data.aws_iam_policy_document.permissions.json
  role        = aws_iam_role.probe.id
}
