terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  # Remote state — swap bucket/table for your own names
  backend "s3" {
    bucket         = "spendi-terraform-state"
    key            = "spendi/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "spendi-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "spendi"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ── Data sources ──────────────────────────────────────────────────────────────

data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" { state = "available" }

locals {
  account_id = data.aws_caller_identity.current.account_id
  azs        = slice(data.aws_availability_zones.available.names, 0, 3)
  name       = "spendi-${var.environment}"
}

# ── VPC ───────────────────────────────────────────────────────────────────────

module "vpc" {
  source = "./modules/vpc"

  name        = local.name
  cidr        = var.vpc_cidr
  azs         = local.azs
  environment = var.environment
}

# ── ECR repositories ──────────────────────────────────────────────────────────

resource "aws_ecr_repository" "backend" {
  name                 = "spendi-backend"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_ecr_repository" "frontend" {
  name                 = "spendi-frontend"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

# Keep only last 10 images to reduce storage costs
resource "aws_ecr_lifecycle_policy" "backend" {
  repository = aws_ecr_repository.backend.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_ecr_lifecycle_policy" "frontend" {
  repository = aws_ecr_repository.frontend.name
  policy     = aws_ecr_lifecycle_policy.backend.policy
}

# ── RDS PostgreSQL ────────────────────────────────────────────────────────────

module "rds" {
  source = "./modules/rds"

  name               = local.name
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  environment        = var.environment
  db_name            = "spendi"
  instance_class     = var.rds_instance_class
}

# ── ElastiCache Redis ─────────────────────────────────────────────────────────

module "redis" {
  source = "./modules/redis"

  name               = local.name
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  node_type          = var.redis_node_type
  environment        = var.environment
}

# ── ECS Fargate ───────────────────────────────────────────────────────────────

module "ecs" {
  source = "./modules/ecs"

  name               = local.name
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  public_subnet_ids  = module.vpc.public_subnet_ids
  private_subnet_ids = module.vpc.private_subnet_ids
  aws_region         = var.aws_region
  account_id         = local.account_id

  backend_image  = "${aws_ecr_repository.backend.repository_url}:latest"
  frontend_image = "${aws_ecr_repository.frontend.repository_url}:latest"

  rds_endpoint        = module.rds.endpoint
  redis_endpoint      = module.redis.endpoint
  db_secret_arn       = module.rds.secret_arn
  app_secrets_arn     = aws_secretsmanager_secret.app_secrets.arn

  domain_name         = var.domain_name
  acm_certificate_arn = var.acm_certificate_arn

  backend_cpu    = var.backend_cpu
  backend_memory = var.backend_memory
  backend_count  = var.backend_desired_count

  frontend_cpu    = var.frontend_cpu
  frontend_memory = var.frontend_memory
  frontend_count  = var.frontend_desired_count
}

# ── Secrets Manager ───────────────────────────────────────────────────────────

resource "aws_secretsmanager_secret" "app_secrets" {
  name                    = "${local.name}/app-secrets"
  recovery_window_in_days = var.environment == "prod" ? 30 : 0

  description = "Spendi application secrets (JWT, encryption keys, OAuth)"
}

# Placeholder — populate via AWS Console or CI/CD secret rotation
resource "aws_secretsmanager_secret_version" "app_secrets" {
  secret_id = aws_secretsmanager_secret.app_secrets.id
  secret_string = jsonencode({
    JWT_SECRET_KEY          = "REPLACE_ME_WITH_SECURE_SECRET"
    ENCRYPTION_MASTER_KEY   = "REPLACE_ME_WITH_64_HEX_CHARS"
    GOOGLE_CLIENT_ID        = "REPLACE_ME"
    GOOGLE_CLIENT_SECRET    = "REPLACE_ME"
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

# ── CloudWatch log groups ─────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/${local.name}/backend"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/${local.name}/frontend"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "celery" {
  name              = "/ecs/${local.name}/celery"
  retention_in_days = 14
}
