output "endpoint"   { value = aws_db_instance.this.address; sensitive = true }
output "secret_arn" { value = aws_secretsmanager_secret.db.arn }
output "sg_id"      { value = aws_security_group.rds.id }
