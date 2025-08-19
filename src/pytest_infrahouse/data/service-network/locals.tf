locals {
  last_az_idx = length(data.aws_availability_zones.available.names) - 1
}
