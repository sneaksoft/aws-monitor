terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "aws-monitor-terraform-state"
    key            = "aws-monitor/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "aws-monitor-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "aws-monitor"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# VPC Module
module "vpc" {
  source = "./modules/vpc"

  project_name = var.project_name
  environment  = var.environment
  vpc_cidr     = var.vpc_cidr
}

# Security Groups
module "security_groups" {
  source = "./modules/security-groups"

  project_name = var.project_name
  environment  = var.environment
  vpc_id       = module.vpc.vpc_id
}

# RDS PostgreSQL
module "rds" {
  source = "./modules/rds"

  project_name        = var.project_name
  environment         = var.environment
  vpc_id              = module.vpc.vpc_id
  subnet_ids          = module.vpc.private_subnet_ids
  security_group_id   = module.security_groups.rds_security_group_id
  db_name             = var.db_name
  db_username         = var.db_username
  db_password         = var.db_password
  db_instance_class   = var.db_instance_class
  db_allocated_storage = var.db_allocated_storage
}

# ElastiCache Redis
module "redis" {
  source = "./modules/redis"

  project_name      = var.project_name
  environment       = var.environment
  vpc_id            = module.vpc.vpc_id
  subnet_ids        = module.vpc.private_subnet_ids
  security_group_id = module.security_groups.redis_security_group_id
  node_type         = var.redis_node_type
}

# ECR Repositories
module "ecr" {
  source = "./modules/ecr"

  project_name = var.project_name
  environment  = var.environment
}

# ECS Cluster and Services
module "ecs" {
  source = "./modules/ecs"

  project_name              = var.project_name
  environment               = var.environment
  vpc_id                    = module.vpc.vpc_id
  public_subnet_ids         = module.vpc.public_subnet_ids
  private_subnet_ids        = module.vpc.private_subnet_ids
  alb_security_group_id     = module.security_groups.alb_security_group_id
  ecs_security_group_id     = module.security_groups.ecs_security_group_id
  backend_ecr_repository_url = module.ecr.backend_repository_url
  frontend_ecr_repository_url = module.ecr.frontend_repository_url
  database_url              = module.rds.connection_string
  redis_url                 = module.redis.connection_string
  cognito_user_pool_id      = var.cognito_user_pool_id
  cognito_client_id         = var.cognito_client_id
  task_role_arn             = module.iam.ecs_task_role_arn
  execution_role_arn        = module.iam.ecs_execution_role_arn
}

# IAM Roles
module "iam" {
  source = "./modules/iam"

  project_name = var.project_name
  environment  = var.environment
  account_id   = data.aws_caller_identity.current.account_id
}

# CloudFront Distribution (optional)
module "cloudfront" {
  source = "./modules/cloudfront"
  count  = var.enable_cloudfront ? 1 : 0

  project_name    = var.project_name
  environment     = var.environment
  alb_domain_name = module.ecs.alb_dns_name
  certificate_arn = var.certificate_arn
}

# Cognito User Pool
module "cognito" {
  source = "./modules/cognito"
  count  = var.create_cognito ? 1 : 0

  project_name = var.project_name
  environment  = var.environment
}
