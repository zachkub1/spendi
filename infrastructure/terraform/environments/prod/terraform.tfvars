environment            = "prod"
aws_region             = "us-east-1"
vpc_cidr               = "10.0.0.0/16"

domain_name            = "ledgerly.app"
acm_certificate_arn    = "arn:aws:acm:us-east-1:ACCOUNT_ID:certificate/CERT_ID"

rds_instance_class     = "db.t4g.small"
redis_node_type        = "cache.t4g.micro"

backend_cpu            = 512
backend_memory         = 1024
backend_desired_count  = 2

frontend_cpu           = 256
frontend_memory        = 512
frontend_desired_count = 2
