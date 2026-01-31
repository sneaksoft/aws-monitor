# ECS Task Execution Role
resource "aws_iam_role" "ecs_execution" {
  name = "${var.project_name}-${var.environment}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-ecs-execution"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Role (for application permissions)
resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-${var.environment}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-ecs-task"
  }
}

# AWS Resource Read-Only Policy
resource "aws_iam_policy" "aws_readonly" {
  name        = "${var.project_name}-${var.environment}-aws-readonly"
  description = "Read-only access to AWS resources for monitoring"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          # EC2
          "ec2:Describe*",
          # RDS
          "rds:Describe*",
          "rds:ListTagsForResource",
          # S3
          "s3:List*",
          "s3:GetBucket*",
          "s3:GetEncryptionConfiguration",
          "s3:GetBucketTagging",
          "s3:GetBucketVersioning",
          "s3:GetPublicAccessBlock",
          # ECS
          "ecs:Describe*",
          "ecs:List*",
          # Lambda
          "lambda:List*",
          "lambda:GetFunction*",
          # ElastiCache
          "elasticache:Describe*",
          # DynamoDB
          "dynamodb:Describe*",
          "dynamodb:List*",
          # ELB
          "elasticloadbalancing:Describe*",
          # IAM (read-only)
          "iam:List*",
          "iam:Get*",
          # CloudWatch
          "cloudwatch:Describe*",
          "cloudwatch:GetMetric*",
          "cloudwatch:ListMetrics",
          "logs:Describe*",
          # Cost Explorer
          "ce:GetCost*",
          "ce:GetReservation*",
          "ce:GetSavings*",
          "ce:GetDimensionValues",
          # KMS
          "kms:List*",
          "kms:Describe*",
          # API Gateway
          "apigateway:GET"
        ]
        Resource = "*"
      }
    ]
  })
}

# AWS Resource Admin Policy (for actions)
resource "aws_iam_policy" "aws_admin" {
  name        = "${var.project_name}-${var.environment}-aws-admin"
  description = "Admin access to AWS resources for actions"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          # EC2 Actions
          "ec2:StartInstances",
          "ec2:StopInstances",
          "ec2:RebootInstances",
          "ec2:TerminateInstances",
          "ec2:DeleteVolume",
          "ec2:DeleteSnapshot",
          # RDS Actions
          "rds:StartDBInstance",
          "rds:StopDBInstance",
          "rds:DeleteDBInstance",
          "rds:CreateDBSnapshot",
          # ECS Actions
          "ecs:UpdateService",
          "ecs:DeleteService",
          # S3 Actions
          "s3:DeleteBucket",
          "s3:DeleteObject*",
          "s3:PutLifecycleConfiguration",
          # ELB Actions
          "elasticloadbalancing:Delete*",
          # Lambda Actions
          "lambda:UpdateFunctionConfiguration"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach policies to task role
resource "aws_iam_role_policy_attachment" "task_readonly" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.aws_readonly.arn
}

resource "aws_iam_role_policy_attachment" "task_admin" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.aws_admin.arn
}

# Future multi-account support: AssumeRole policy
resource "aws_iam_policy" "assume_role" {
  name        = "${var.project_name}-${var.environment}-assume-role"
  description = "Allow assuming roles in other accounts"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "sts:AssumeRole"
        Resource = "arn:aws:iam::*:role/${var.project_name}-*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "task_assume_role" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.assume_role.arn
}
