variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (staging | prod)"
  type        = string
  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "Environment must be 'staging' or 'prod'."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "domain_name" {
  description = "Root domain name (e.g. spendi.app)"
  type        = string
}

variable "acm_certificate_arn" {
  description = "ARN of the ACM TLS certificate for the domain"
  type        = string
}

# ── RDS ───────────────────────────────────────────────────────────────────────

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.micro"
}

# ── Redis ─────────────────────────────────────────────────────────────────────

variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t4g.micro"
}

# ── ECS — Backend ─────────────────────────────────────────────────────────────

variable "backend_cpu" {
  type    = number
  default = 512
}

variable "backend_memory" {
  type    = number
  default = 1024
}

variable "backend_desired_count" {
  type    = number
  default = 2
}

# ── ECS — Frontend ────────────────────────────────────────────────────────────

variable "frontend_cpu" {
  type    = number
  default = 256
}

variable "frontend_memory" {
  type    = number
  default = 512
}

variable "frontend_desired_count" {
  type    = number
  default = 2
}
