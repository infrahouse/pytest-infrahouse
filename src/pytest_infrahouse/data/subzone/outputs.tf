output "subzone_id" {
  description = "Route53 hosted zone ID of the created subzone"
  value       = aws_route53_zone.subzone.zone_id
}
