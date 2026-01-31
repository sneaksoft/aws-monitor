"""Audit logging service."""

from typing import Any, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.database import AuditLog, User
from app.config import get_settings

settings = get_settings()


class AuditService:
    """Service for audit logging."""

    async def log_action(
        self,
        user: User,
        action: str,
        resource_type: str,
        resource_ids: list[str],
        request: Request,
        status: str,
        request_data: Optional[dict[str, Any]] = None,
        response_data: Optional[dict[str, Any]] = None,
        aws_account_id: Optional[str] = None,
        region: Optional[str] = None,
    ) -> None:
        """Log an action to the audit log."""
        # Get client info
        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        async with async_session_maker() as session:
            for resource_id in resource_ids:
                log_entry = AuditLog(
                    user_id=user.id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    aws_account_id=aws_account_id or settings.aws_region,
                    region=region or settings.aws_region,
                    request_data=request_data,
                    response_data=response_data,
                    status=status,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                session.add(log_entry)

            await session.commit()

    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP from request."""
        # Check for forwarded headers (behind proxy/load balancer)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # Take the first IP in the chain
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct connection
        if request.client:
            return request.client.host

        return None

    async def get_recent_actions(
        self,
        resource_id: str,
        limit: int = 10,
    ) -> list[AuditLog]:
        """Get recent audit logs for a resource."""
        from sqlalchemy import select, desc

        async with async_session_maker() as session:
            query = (
                select(AuditLog)
                .where(AuditLog.resource_id == resource_id)
                .order_by(desc(AuditLog.created_at))
                .limit(limit)
            )
            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_user_actions(
        self,
        user_id: str,
        limit: int = 50,
    ) -> list[AuditLog]:
        """Get recent actions by a user."""
        from sqlalchemy import select, desc

        async with async_session_maker() as session:
            query = (
                select(AuditLog)
                .where(AuditLog.user_id == user_id)
                .order_by(desc(AuditLog.created_at))
                .limit(limit)
            )
            result = await session.execute(query)
            return list(result.scalars().all())
