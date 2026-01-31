"""Audit log endpoints."""

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import RequireAdmin
from app.models.database import AuditLog, User
from app.models.schemas import AuditLogResponse, AuditLogListResponse

router = APIRouter()


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    user: RequireAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    action: Optional[str] = Query(None, description="Filter by action type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    user_email: Optional[str] = Query(None, description="Filter by user email"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """List audit logs with filtering and pagination (admin only)."""
    # Build query
    query = select(AuditLog).join(User, AuditLog.user_id == User.id, isouter=True)

    if action:
        query = query.where(AuditLog.action.ilike(f"%{action}%"))
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if user_email:
        query = query.where(User.email.ilike(f"%{user_email}%"))
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)
    if status:
        query = query.where(AuditLog.status == status)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Paginate
    query = query.order_by(desc(AuditLog.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    # Build response with user emails
    items = []
    for log in logs:
        log_response = AuditLogResponse(
            id=log.id,
            user_email=log.user.email if log.user else None,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            aws_account_id=log.aws_account_id,
            region=log.region,
            status=log.status,
            request_data=log.request_data,
            created_at=log.created_at,
        )
        items.append(log_response)

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: str,
    user: RequireAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get detailed audit log entry (admin only)."""
    query = select(AuditLog).where(AuditLog.id == log_id)
    result = await db.execute(query)
    log = result.scalar_one_or_none()

    if not log:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Audit log not found")

    return AuditLogResponse(
        id=log.id,
        user_email=log.user.email if log.user else None,
        action=log.action,
        resource_type=log.resource_type,
        resource_id=log.resource_id,
        aws_account_id=log.aws_account_id,
        region=log.region,
        status=log.status,
        request_data=log.request_data,
        created_at=log.created_at,
    )
