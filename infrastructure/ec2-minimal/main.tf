terraform {
  required_version = ">= 1.7"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  # Optional: use S3 backend once you have a bucket
  # backend "s3" { bucket = "...", key = "spendi/ec2.tfstate", region = "us-east-1", encrypt = true }
}

provider "aws" {
  region = var.aws_region
  default_tags { tags = { Project = "spendi", ManagedBy = "terraform" } }
}

data "aws_availability_zones" "available" { state = "available" }

# ── VPC (minimal — single public subnet, no NAT gateway) ─────────────────────
# NAT gateways cost $32/mo. We put the EC2 in a public subnet instead.

resource "aws_vpc" "this" {
  cidr_block           = "10.0.0.0/24"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.this.id
  cidr_block              = "10.0.0.0/25"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true
}

# Second subnet in a different AZ — required by RDS subnet group
resource "aws_subnet" "public_b" {
  vpc_id                  = aws_vpc.this.id
  cidr_block              = "10.0.0.128/25"
  availability_zone       = data.aws_availability_zones.available.names[1]
  map_public_ip_on_launch = false
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  route { cidr_block = "0.0.0.0/0"; gateway_id = aws_internet_gateway.this.id }
}
resource "aws_route_table_association" "public"   { subnet_id = aws_subnet.public.id;   route_table_id = aws_route_table.public.id }
resource "aws_route_table_association" "public_b" { subnet_id = aws_subnet.public_b.id; route_table_id = aws_route_table.public.id }

# ── Security groups ───────────────────────────────────────────────────────────

resource "aws_security_group" "ec2" {
  name        = "spendi-ec2"
  description = "Allow HTTP, HTTPS, SSH"
  vpc_id      = aws_vpc.this.id

  ingress { description = "HTTPS"; from_port = 443; to_port = 443; protocol = "tcp"; cidr_blocks = ["0.0.0.0/0"] }
  ingress { description = "HTTP";  from_port = 80;  to_port = 80;  protocol = "tcp"; cidr_blocks = ["0.0.0.0/0"] }
  # SSH: restrict to your IP in production — set var.allowed_ssh_cidr
  ingress { description = "SSH";   from_port = 22;  to_port = 22;  protocol = "tcp"; cidr_blocks = [var.allowed_ssh_cidr] }

  egress { from_port = 0; to_port = 0; protocol = "-1"; cidr_blocks = ["0.0.0.0/0"] }
}

resource "aws_security_group" "rds" {
  name        = "spendi-rds"
  description = "Allow PostgreSQL from EC2 only"
  vpc_id      = aws_vpc.this.id

  ingress {
    description     = "PostgreSQL from EC2"
    from_port       = 5432; to_port = 5432; protocol = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }
  egress { from_port = 0; to_port = 0; protocol = "-1"; cidr_blocks = ["0.0.0.0/0"] }
}

# ── Elastic IP (free while attached) ─────────────────────────────────────────

resource "aws_eip" "this" {
  domain   = "vpc"
  instance = aws_instance.this.id
  depends_on = [aws_internet_gateway.this]
}

# ── EC2 t2.micro — FREE TIER for 12 months ───────────────────────────────────

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  filter { name = "name";          values = ["al2023-ami-*-x86_64"] }
  filter { name = "architecture";  values = ["x86_64"] }
}

resource "aws_key_pair" "this" {
  key_name   = "spendi-key"
  public_key = file(var.ssh_public_key_path)
}

resource "aws_instance" "this" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t2.micro"   # FREE TIER (750 hr/mo for 12 months)
  key_name               = aws_key_pair.this.key_name
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.ec2.id]

  root_block_device {
    volume_type = "gp3"
    volume_size = 20   # 30 GB free tier; keeping 20 to leave room
    encrypted   = true
  }

  user_data = templatefile("${path.module}/user_data.sh", {
    db_host     = aws_db_instance.this.address
    domain_name = var.domain_name
  })

  # Automatically recover on hardware failure
  maintenance_options { auto_recovery = "default" }

  tags = { Name = "spendi-app" }
}

# ── RDS db.t2.micro — FREE TIER for 12 months ────────────────────────────────

resource "random_password" "db" {
  length  = 32
  special = false   # avoid special chars that break connection strings
}

resource "aws_db_subnet_group" "this" {
  name       = "spendi-db-subnet"
  subnet_ids = [aws_subnet.public.id, aws_subnet.public_b.id]
}

resource "aws_db_instance" "this" {
  identifier        = "spendi"
  engine            = "postgres"
  engine_version    = "16.2"
  instance_class    = "db.t3.micro"  # FREE TIER (750 hr/mo for 12 months)
  allocated_storage = 20              # FREE TIER (20 GB)
  storage_type      = "gp2"
  storage_encrypted = true

  db_name  = "spendi"
  username = "spendi"
  password = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  # Keep costs at zero — no Multi-AZ, no backups beyond 0 for dev
  multi_az                = false
  publicly_accessible     = false
  backup_retention_period = 3
  skip_final_snapshot     = true
  deletion_protection     = false

  # Log slow queries (included in free tier)
  parameter_group_name = aws_db_parameter_group.this.name
}

resource "aws_db_parameter_group" "this" {
  name   = "spendi-pg16"
  family = "postgres16"
  parameter { name = "log_min_duration_statement"; value = "2000" }
}

# Store DB password in Secrets Manager (free for first 30 days, then $0.40/mo)
# Alternatively skip this and paste into EC2 .env directly.
resource "aws_secretsmanager_secret" "db" {
  name                    = "spendi/db-password"
  recovery_window_in_days = 0
}
resource "aws_secretsmanager_secret_version" "db" {
  secret_id     = aws_secretsmanager_secret.db.id
  secret_string = random_password.db.result
}

# ── Route53 (optional — $0.50/mo for hosted zone) ────────────────────────────
# Comment this block out if you don't have a domain yet.

resource "aws_route53_zone" "this" {
  count = var.domain_name != "" ? 1 : 0
  name  = var.domain_name
}

resource "aws_route53_record" "app" {
  count   = var.domain_name != "" ? 1 : 0
  zone_id = aws_route53_zone.this[0].zone_id
  name    = var.domain_name
  type    = "A"
  ttl     = 300
  records = [aws_eip.this.public_ip]
}

resource "aws_route53_record" "api" {
  count   = var.domain_name != "" ? 1 : 0
  zone_id = aws_route53_zone.this[0].zone_id
  name    = "api.${var.domain_name}"
  type    = "A"
  ttl     = 300
  records = [aws_eip.this.public_ip]
}
