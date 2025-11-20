terraform {
  required_version = ">= 1.5.0"

  //noinspection HILUnresolvedReference
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.11, < 7.0"
    }
  }
}
