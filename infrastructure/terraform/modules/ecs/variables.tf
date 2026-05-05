variable "name"               { type = string }
variable "environment"        { type = string }
variable "vpc_id"             { type = string }
variable "public_subnet_ids"  { type = list(string) }
variable "private_subnet_ids" { type = list(string) }
variable "aws_region"         { type = string }
variable "account_id"         { type = string }

variable "backend_image"      { type = string }
variable "frontend_image"     { type = string }

variable "rds_endpoint"       { type = string }
variable "redis_endpoint"     { type = string }
variable "db_secret_arn"      { type = string }
variable "app_secrets_arn"    { type = string }

variable "domain_name"        { type = string }
variable "acm_certificate_arn" { type = string }

variable "backend_cpu"        { type = number; default = 512 }
variable "backend_memory"     { type = number; default = 1024 }
variable "backend_count"      { type = number; default = 2 }

variable "frontend_cpu"       { type = number; default = 256 }
variable "frontend_memory"    { type = number; default = 512 }
variable "frontend_count"     { type = number; default = 2 }
