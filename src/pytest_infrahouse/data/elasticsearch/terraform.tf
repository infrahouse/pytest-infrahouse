terraform {
  required_version = ">= 1.5.0"

  //noinspection HILUnresolvedReference
  required_providers {
    aws = {
      source = "hashicorp/aws"
      # != 6.28.0 excluded due to bug https://github.com/hashicorp/terraform-provider-aws/issues/46016
      version = ">= 5.11, < 7.0, != 6.28.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.1"
    }
  }
}
