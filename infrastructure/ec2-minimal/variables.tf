variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "domain_name" {
  description = "Your domain (e.g. spendi.app). Leave empty to skip Route53."
  type        = string
  default     = ""
}

variable "ssh_public_key_path" {
  description = "Path to your SSH public key file"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "allowed_ssh_cidr" {
  description = "CIDR allowed to SSH in. Use your home IP: curl ifconfig.me/ip"
  type        = string
  default     = "0.0.0.0/0"  # CHANGE THIS to your IP/32 in production
}
