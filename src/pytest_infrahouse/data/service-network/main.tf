locals {
  # Flow logs bucket replica must live outside the test region.
  replication_region = var.region == "us-east-1" ? "us-west-1" : "us-east-1"
}

module "service-network" {
  source                  = "registry.infrahouse.com/infrahouse/service-network/aws"
  version                 = "5.0.1"
  service_name            = "service-network"
  environment             = var.environment
  vpc_cidr_block          = "10.1.0.0/16"
  management_cidr_block   = "10.1.0.0/16"
  enable_dns_hostnames    = true
  enable_dns_support      = true
  replication_region      = local.replication_region
  flow_logs_force_destroy = true
  subnets = [
    {
      cidr                    = "10.1.0.0/24"
      availability-zone       = data.aws_availability_zones.available.names[0]
      map_public_ip_on_launch = true
      create_nat              = true
      forward_to              = null
    },
    {
      cidr                    = "10.1.1.0/24"
      availability-zone       = data.aws_availability_zones.available.names[1]
      map_public_ip_on_launch = true
      create_nat              = false
      forward_to              = null
    },
    {
      cidr                    = "10.1.100.0/24"
      availability-zone       = data.aws_availability_zones.available.names[0]
      map_public_ip_on_launch = false
      create_nat              = false
      forward_to              = "10.1.0.0/24"
    },
    {
      cidr                    = "10.1.101.0/24"
      availability-zone       = data.aws_availability_zones.available.names[1]
      map_public_ip_on_launch = false
      create_nat              = false
      forward_to              = "10.1.0.0/24" # to a network with NAT
    },
  ]
}
