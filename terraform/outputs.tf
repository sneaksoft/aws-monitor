output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "alb_dns_name" {
  description = "Application Load Balancer DNS name"
  value       = module.ecs.alb_dns_name
}

output "backend_ecr_repository_url" {
  description = "Backend ECR repository URL"
  value       = module.ecr.backend_repository_url
}

output "frontend_ecr_repository_url" {
  description = "Frontend ECR repository URL"
  value       = module.ecr.frontend_repository_url
}

output "rds_endpoint" {
  description = "RDS endpoint"
  value       = module.rds.endpoint
}

output "redis_endpoint" {
  description = "Redis endpoint"
  value       = module.redis.endpoint
}

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = var.create_cognito ? module.cognito[0].user_pool_id : var.cognito_user_pool_id
}

output "cognito_client_id" {
  description = "Cognito Client ID"
  value       = var.create_cognito ? module.cognito[0].client_id : var.cognito_client_id
}

output "cloudfront_distribution_domain" {
  description = "CloudFront distribution domain name"
  value       = var.enable_cloudfront ? module.cloudfront[0].distribution_domain_name : null
}
