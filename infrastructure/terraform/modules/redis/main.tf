resource "aws_security_group" "redis" {
  name        = "${var.name}-redis-sg"
  description = "Allow Redis from ECS tasks only"
  vpc_id      = var.vpc_id

  ingress {
    description = "Redis from ECS"
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_elasticache_subnet_group" "this" {
  name       = "${var.name}-redis-subnet-group"
  subnet_ids = var.private_subnet_ids
}

resource "aws_elasticache_replication_group" "this" {
  replication_group_id = "${var.name}-redis"
  description          = "Spendi Redis (Celery broker + result backend)"

  node_type            = var.node_type
  num_cache_clusters   = var.environment == "prod" ? 2 : 1
  automatic_failover_enabled = var.environment == "prod"

  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.this.name
  security_group_ids   = [aws_security_group.redis.id]

  # Encryption at rest and in transit
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  # Snapshots
  snapshot_retention_limit = var.environment == "prod" ? 3 : 0
  snapshot_window          = "02:00-03:00"

  # Engine
  engine_version = "7.1"

  apply_immediately = var.environment != "prod"
}
