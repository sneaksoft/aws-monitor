"""Integration tests for audit endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AuditLog, User


@pytest.mark.asyncio
async def test_list_audit_logs(
    client: AsyncClient, db_session: AsyncSession, test_user: User
):
    """Test listing audit logs."""
    # Create some audit logs
    for i in range(3):
        log = AuditLog(
            user_id=test_user.id,
            action=f"ec2:start",
            resource_type="ec2",
            resource_id=f"i-{i}",
            status="success",
        )
        db_session.add(log)
    await db_session.commit()

    response = await client.get("/api/audit")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


@pytest.mark.asyncio
async def test_list_audit_logs_with_filters(
    client: AsyncClient, db_session: AsyncSession, test_user: User
):
    """Test listing audit logs with filters."""
    # Create audit logs with different actions
    actions = ["ec2:start", "ec2:stop", "rds:start"]
    for i, action in enumerate(actions):
        log = AuditLog(
            user_id=test_user.id,
            action=action,
            resource_type=action.split(":")[0],
            resource_id=f"resource-{i}",
            status="success",
        )
        db_session.add(log)
    await db_session.commit()

    response = await client.get("/api/audit?action=ec2:start")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["action"] == "ec2:start"


@pytest.mark.asyncio
async def test_list_audit_logs_requires_admin(readonly_client: AsyncClient):
    """Test that audit logs require admin role."""
    response = await readonly_client.get("/api/audit")

    assert response.status_code == 403
