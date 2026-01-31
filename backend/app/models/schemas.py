"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr


# User schemas
class UserBase(BaseModel):
    email: EmailStr
    role: str = "readonly"


class UserCreate(UserBase):
    cognito_sub: str


class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# AWS Account schemas
class AWSAccountBase(BaseModel):
    account_id: str = Field(..., min_length=12, max_length=12)
    account_name: Optional[str] = None
    role_arn: str
    external_id: Optional[str] = None
    enabled: bool = True


class AWSAccountCreate(AWSAccountBase):
    pass


class AWSAccountResponse(AWSAccountBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# Resource schemas
class ResourceBase(BaseModel):
    resource_id: str
    resource_type: str
    name: Optional[str] = None
    region: str
    aws_account_id: str
    state: Optional[str] = None
    tags: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResourceResponse(ResourceBase):
    created_at: Optional[datetime] = None
    monthly_cost: Optional[float] = None


class ResourceListResponse(BaseModel):
    items: list[ResourceResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class ResourceFilters(BaseModel):
    resource_type: Optional[str] = None
    region: Optional[str] = None
    state: Optional[str] = None
    tag_key: Optional[str] = None
    tag_value: Optional[str] = None
    search: Optional[str] = None


# Action schemas
class ActionRequest(BaseModel):
    resource_ids: list[str]
    dry_run: bool = True
    override_code: Optional[str] = None


class EC2ActionRequest(ActionRequest):
    instance_ids: list[str] = Field(..., alias="resource_ids")


class RDSActionRequest(ActionRequest):
    db_instance_identifier: str


class ECSScaleRequest(ActionRequest):
    cluster: str
    service: str
    desired_count: int = Field(..., ge=0)


class S3DeleteRequest(ActionRequest):
    bucket_name: str
    force_delete: bool = False


class ActionResponse(BaseModel):
    status: str
    action: str
    resource_ids: list[str]
    dry_run: bool
    message: Optional[str] = None
    details: Optional[dict[str, Any]] = None


# Cost schemas
class CostSummaryResponse(BaseModel):
    mtd_cost: float
    mtd_forecast: float
    last_month_cost: float
    ytd_cost: float
    currency: str = "USD"
    period_start: datetime
    period_end: datetime


class CostByService(BaseModel):
    service: str
    cost: float
    percentage: float


class CostByRegion(BaseModel):
    region: str
    cost: float
    percentage: float


class CostBreakdownResponse(BaseModel):
    by_service: list[CostByService]
    by_region: list[CostByRegion]
    total: float
    currency: str = "USD"
    period_start: datetime
    period_end: datetime


class CostForecastResponse(BaseModel):
    forecasted_cost: float
    confidence_level: float
    period_start: datetime
    period_end: datetime
    currency: str = "USD"


class CostRecommendation(BaseModel):
    resource_id: str
    resource_type: str
    recommendation_type: str
    description: str
    estimated_monthly_savings: float
    current_monthly_cost: float
    priority: str  # high, medium, low


class CostRecommendationsResponse(BaseModel):
    recommendations: list[CostRecommendation]
    total_potential_savings: float
    currency: str = "USD"


# Audit schemas
class AuditLogResponse(BaseModel):
    id: UUID
    user_email: Optional[str] = None
    action: str
    resource_type: str
    resource_id: str
    aws_account_id: Optional[str] = None
    region: Optional[str] = None
    status: str
    request_data: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# Auth schemas
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str
