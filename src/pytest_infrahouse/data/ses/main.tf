resource "aws_ses_domain_identity" "ses_domain" {
  domain = data.aws_route53_zone.test-zone.name
}

resource "aws_route53_record" "amazonses_verification_record" {
  zone_id = data.aws_route53_zone.test-zone.zone_id
  name    = "_amazonses.${data.aws_route53_zone.test-zone.name}"
  type    = "TXT"
  ttl     = "600"
  records = [
    aws_ses_domain_identity.ses_domain.verification_token
  ]
}

resource "aws_ses_domain_identity_verification" "verification" {
  domain = aws_ses_domain_identity.ses_domain.domain
  depends_on = [
    aws_route53_record.amazonses_verification_record
  ]
}
