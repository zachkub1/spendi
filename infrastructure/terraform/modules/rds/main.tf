resource "random_password" "db" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "aws_secretsmanager_secret" "db" {
  name                    = "${var.name}/db-credentials"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id = aws_secretsmanager_secret.db.id
  secret_string = jsonencode({
    username = "spendi"
    password = random_password.db.result
    host     = aws_db_instance.this.address
    port     = 5432
    dbname   = var.db_name
  })
}

# ── Security group ────────────────────────────────────────────────────────────

resource "aws_security_group" "rds" {
  name        = "${var.name}-rds-sg"
  description = "Allow PostgreSQL from ECS tasks only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "PostgreSQL from ECS"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.ecs_sg_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ── Subnet group ──────────────────────────────────────────────────────────────

resource "aws_db_subnet_group" "this" {
  name       = "${var.name}-db-subnet-group"
  subnet_ids = var.private_subnet_ids
}

# ── RDS Instance ──────────────────────────────────────────────────────────────

resource "aws_db_instance" "this" {
  identifier        = "${var.name}-postgres"
  engine            = "postgres"
  engine_version    = "16.2"
  instance_class    = var.instance_class
  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = var.db_name
  username = "spendi"
  password = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  # High availability
  multi_az = var.environment == "prod"

  # Backup
  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  # Security
  publicly_accessible     = false
  deletion_protection     = var.environment == "prod"
  skip_final_snapshot     = var.environment != "prod"
  final_snapshot_identifier = "${var.name}-final-snapshot"

  # Performance Insights (free tier = 7 days)
  performance_insights_enabled          = true
  performance_insights_retention_period = 7

  # Parameter group for connection settings
  parameter_group_name = aws_db_parameter_group.this.name
}

resource "aws_db_parameter_group" "this" {
  name   = "${var.name}-pg16"
  family = "postgres16"

  parameter {
    name  = "log_connections"
    value = "1"
  }
  parameter {
    name  = "log_disconnections"
    value = "1"
  }
  parameter {
    name  = "log_min_duration_statement"
    value = "1000"  # log queries > 1s
  }
}
