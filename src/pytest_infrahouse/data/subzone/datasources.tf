data "aws_route53_zone" "parent" {
  name = var.parent_zone_name
}
