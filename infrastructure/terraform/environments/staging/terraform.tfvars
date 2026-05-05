environment            = "staging"
aws_region             = "us-east-1"
vpc_cidr               = "10.1.0.0/16"

domain_name            = "staging.ledgerly.app"
acm_certificate_arn    = "arn:aws:acm:us-east-1:ACCOUNT_ID:certificate/STAGING_CERT_ID"

rds_instance_class     = "db.t4g.micro"
redis_node_type        = "cache.t4g.micro"

backend_cpu            = 256
backend_memory         = 512
backend_desired_count  = 1

frontend_cpu           = 256
frontend_memory        = 512
frontend_desired_count = 1
