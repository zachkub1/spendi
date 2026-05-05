variable "name"               { type = string }
variable "vpc_id"             { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "environment"        { type = string }
variable "db_name"            { type = string }
variable "instance_class"     { type = string }
variable "ecs_sg_id"          { type = string; default = "" }
