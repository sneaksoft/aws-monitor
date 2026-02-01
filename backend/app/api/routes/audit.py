"""Audit log endpoints."""

import csv
import io
import json
from datetime import datetime
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import RequireAdmin
from app.models.database import AuditLog, User
from app.models.schemas import AuditLogResponse, AuditLogListResponse

router = APIRouter()

MAX_EXPORT_RECORDS = 10000


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
            response_data=log.response_data,
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


@router.get("/export")
async def export_audit_logs(
    user: RequireAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
    format: Literal["csv", "json"] = Query("csv", description="Export format"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    user_email: Optional[str] = Query(None, description="Filter by user email"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """Export audit logs as CSV or JSON (admin only). Max 10,000 records."""
    # Build query with same filters as list endpoint
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

    # Order and limit
    query = query.order_by(desc(AuditLog.created_at)).limit(MAX_EXPORT_RECORDS)

    result = await db.execute(query)
    logs = result.scalars().all()

    if format == "json":
        # Export as JSON
        export_data = []
        for log in logs:
            export_data.append({
                "id": str(log.id),
                "user_email": log.user.email if log.user else None,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "aws_account_id": log.aws_account_id,
                "region": log.region,
                "status": log.status,
                "request_data": log.request_data,
                "response_data": log.response_data,
                "created_at": log.created_at.isoformat(),
            })

        json_content = json.dumps(export_data, indent=2)
        return StreamingResponse(
            io.StringIO(json_content),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=audit_logs.json"},
        )
    else:
        # Export as CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Header row
        writer.writerow([
            "id", "user_email", "action", "resource_type", "resource_id",
            "aws_account_id", "region", "status", "request_data", "response_data", "created_at"
        ])

        # Data rows
        for log in logs:
            writer.writerow([
                str(log.id),
                log.user.email if log.user else "",
                log.action,
                log.resource_type,
                log.resource_id,
                log.aws_account_id or "",
                log.region or "",
                log.status,
                json.dumps(log.request_data) if log.request_data else "",
                json.dumps(log.response_data) if log.response_data else "",
                log.created_at.isoformat(),
            ])

        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
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
        response_data=log.response_data,
        created_at=log.created_at,
    )
