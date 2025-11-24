# Data sources for VPC information
data "aws_subnet" "selected" {
  id = var.subnet_private_ids[0]
}

data "aws_vpc" "selected" {
  id = data.aws_subnet.selected.vpc_id
}

# Security group for PostgreSQL RDS instance
resource "aws_security_group" "postgres" {
  name_prefix = "${var.db_identifier}-"
  description = "Security group for PostgreSQL RDS test instance"
  vpc_id      = data.aws_vpc.selected.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name = var.db_identifier
  }
}

# Allow incoming PostgreSQL connections from VPC
resource "aws_security_group_rule" "postgres_ingress" {
  type              = "ingress"
  from_port         = 5432
  to_port           = 5432
  protocol          = "tcp"
  cidr_blocks       = [data.aws_vpc.selected.cidr_block]
  security_group_id = aws_security_group.postgres.id
  description       = "Allow PostgreSQL connections from VPC"
}

# DB subnet group for RDS
resource "aws_db_subnet_group" "postgres" {
  name_prefix = "${var.db_identifier}-"
  subnet_ids  = var.subnet_private_ids

  tags = {
    Name = "${var.db_identifier}-subnet-group"
  }
}

# Generate secure password for database
resource "random_password" "postgres_password" {
  length  = 32
  special = true
  # Avoid problematic special characters for database passwords
  override_special = "!#$%&*()-_=+[]{}:?"
}

# Store password in Secrets Manager for secure access
resource "aws_secretsmanager_secret" "postgres_password" {
  name_prefix             = "${var.db_identifier}-password-"
  description             = "PostgreSQL master password for ${aws_db_instance.postgres.identifier}"
  recovery_window_in_days = 0 # Immediate deletion for test environments

  tags = {
    Name = "${var.db_identifier}-password"
  }
}

resource "aws_secretsmanager_secret_version" "postgres_password" {
  secret_id = aws_secretsmanager_secret.postgres_password.id
  secret_string = jsonencode({
    username = var.master_username
    password = random_password.postgres_password.result
    engine   = "postgres"
    host     = aws_db_instance.postgres.address
    port     = aws_db_instance.postgres.port
    dbname   = var.database_name
  })
}

# IAM role for Enhanced Monitoring (optional but recommended)
data "aws_iam_policy_document" "rds_enhanced_monitoring_assume" {
  count = var.enable_enhanced_monitoring ? 1 : 0

  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["monitoring.rds.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "rds_enhanced_monitoring" {
  count = var.enable_enhanced_monitoring ? 1 : 0

  name_prefix        = "${var.db_identifier}-monitoring-"
  assume_role_policy = data.aws_iam_policy_document.rds_enhanced_monitoring_assume[0].json

  tags = {
    Name = "${var.db_identifier}-monitoring"
  }
}

resource "aws_iam_role_policy_attachment" "rds_enhanced_monitoring" {
  count = var.enable_enhanced_monitoring ? 1 : 0

  role       = aws_iam_role.rds_enhanced_monitoring[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# Generate unique suffix for RDS instance identifier
resource "random_id" "postgres_suffix" {
  byte_length = 4
}

# PostgreSQL RDS instance
resource "aws_db_instance" "postgres" {
  identifier = "${var.db_identifier}-${random_id.postgres_suffix.hex}"

  # Engine configuration
  engine         = "postgres"
  engine_version = var.postgres_version
  instance_class = var.instance_class

  # Storage configuration
  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true

  # Database configuration
  db_name  = var.database_name
  username = var.master_username
  password = random_password.postgres_password.result
  port     = 5432

  # Network configuration
  db_subnet_group_name   = aws_db_subnet_group.postgres.name
  vpc_security_group_ids = [aws_security_group.postgres.id]
  publicly_accessible    = false

  # Backup configuration - minimal for testing
  backup_retention_period = var.backup_retention_period
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  # Test-friendly settings
  skip_final_snapshot        = true
  deletion_protection        = false
  apply_immediately          = true
  auto_minor_version_upgrade = false

  # Performance Insights (optional)
  performance_insights_enabled          = var.enable_performance_insights
  performance_insights_retention_period = var.enable_performance_insights ? 7 : null

  # Enhanced Monitoring (optional)
  enabled_cloudwatch_logs_exports = var.enabled_cloudwatch_logs_exports
  monitoring_interval             = var.enable_enhanced_monitoring ? 60 : 0
  monitoring_role_arn             = var.enable_enhanced_monitoring ? aws_iam_role.rds_enhanced_monitoring[0].arn : null

  tags = {
    Name = var.db_identifier
  }

  depends_on = [
    aws_iam_role_policy_attachment.rds_enhanced_monitoring
  ]
}

# Wait for database to be available
resource "time_sleep" "wait_for_postgres" {
  depends_on = [aws_db_instance.postgres]

  create_duration = "30s"
}
