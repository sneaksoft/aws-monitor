variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "aws-monitor"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

# Database
variable "db_name" {
  description = "Database name"
  type        = string
  default     = "aws_monitor"
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "aws_monitor"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.small"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

# Redis
variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.micro"
}

# Cognito
variable "cognito_user_pool_id" {
  description = "Cognito User Pool ID (if using existing)"
  type        = string
  default     = ""
}

variable "cognito_client_id" {
  description = "Cognito Client ID (if using existing)"
  type        = string
  default     = ""
}

variable "create_cognito" {
  description = "Create new Cognito User Pool"
  type        = bool
  default     = true
}

# CloudFront
variable "enable_cloudfront" {
  description = "Enable CloudFront distribution"
  type        = bool
  default     = false
}

variable "certificate_arn" {
  description = "ACM certificate ARN for CloudFront"
  type        = string
  default     = ""
}

# Admin
variable "admin_override_code" {
  description = "Admin override code for production resources"
  type        = string
  sensitive   = true
  default     = ""
}
