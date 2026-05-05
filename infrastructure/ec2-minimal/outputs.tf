output "public_ip" {
  description = "EC2 public IP — point your domain A record here"
  value       = aws_eip.this.public_ip
}

output "rds_host" {
  description = "RDS endpoint (private — only reachable from EC2)"
  value       = aws_db_instance.this.address
  sensitive   = true
}

output "db_password_secret_arn" {
  description = "ARN of the Secrets Manager secret holding the DB password"
  value       = aws_secretsmanager_secret.db.arn
}

output "ssh_command" {
  description = "How to SSH into your server"
  value       = "ssh -i ~/.ssh/id_rsa ec2-user@${aws_eip.this.public_ip}"
}
