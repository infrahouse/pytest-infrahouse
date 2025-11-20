provider "aws" {
  region = var.region
  dynamic "assume_role" {
    for_each = var.role_arn != null ? [1] : []
    content {
      role_arn = var.role_arn
    }
  }
  default_tags {
    tags = {
      created_by_test : var.calling_test
      created_by_fixture : "infrahouse/pytest-infrahouse/elasticsearch"
    }
  }
}
