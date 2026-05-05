output "alb_dns_name" {
  description = "ALB DNS name — point your Route53 A-alias record here"
  value       = module.ecs.alb_dns_name
}

output "ecr_backend_url" {
  description = "ECR backend repository URL"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_url" {
  description = "ECR frontend repository URL"
  value       = aws_ecr_repository.frontend.repository_url
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint (private)"
  value       = module.rds.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint (private)"
  value       = module.redis.endpoint
  sensitive   = true
}

output "app_secrets_arn" {
  description = "ARN of the Secrets Manager secret containing app credentials"
  value       = aws_secretsmanager_secret.app_secrets.arn
}
