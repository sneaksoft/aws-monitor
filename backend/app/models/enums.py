"""Enumeration types for the application."""

from enum import Enum


class UserRole(str, Enum):
    """User role enumeration."""

    ADMIN = "admin"
    OPERATOR = "operator"
    READONLY = "readonly"


class ActionStatus(str, Enum):
    """Action execution status."""

    SUCCESS = "success"
    FAILED = "failed"
    DRY_RUN = "dry_run"
    PENDING = "pending"


class ResourceType(str, Enum):
    """AWS resource types supported."""

    EC2 = "ec2"
    RDS = "rds"
    S3 = "s3"
    ECS = "ecs"
    LAMBDA = "lambda"
    EBS = "ebs"
    ELB = "elb"
    VPC = "vpc"
    ELASTICACHE = "elasticache"
    DYNAMODB = "dynamodb"


class EC2State(str, Enum):
    """EC2 instance states."""

    PENDING = "pending"
    RUNNING = "running"
    SHUTTING_DOWN = "shutting-down"
    TERMINATED = "terminated"
    STOPPING = "stopping"
    STOPPED = "stopped"


class RDSState(str, Enum):
    """RDS instance states."""

    AVAILABLE = "available"
    BACKING_UP = "backing-up"
    CREATING = "creating"
    DELETING = "deleting"
    FAILED = "failed"
    MAINTENANCE = "maintenance"
    MODIFYING = "modifying"
    REBOOTING = "rebooting"
    STARTING = "starting"
    STOPPED = "stopped"
    STOPPING = "stopping"
    STORAGE_FULL = "storage-full"
