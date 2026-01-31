"""Integration tests for actions endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ec2_start_dry_run(client: AsyncClient):
    """Test EC2 start action with dry run."""
    with patch("app.api.routes.actions.EC2Service") as mock_ec2_class:
        mock_ec2 = AsyncMock()
        mock_ec2.start_instances.return_value = {
            "would_start": ["i-1234567890"],
            "dry_run": True,
        }
        mock_ec2_class.return_value = mock_ec2

        with patch("app.api.routes.actions.AuditService") as mock_audit_class:
            mock_audit = AsyncMock()
            mock_audit_class.return_value = mock_audit

            response = await client.post(
                "/api/actions/ec2/start",
                json={"resource_ids": ["i-1234567890"], "dry_run": True},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "dry_run"
            assert data["dry_run"] is True


@pytest.mark.asyncio
async def test_ec2_stop_with_protection_check(client: AsyncClient):
    """Test EC2 stop action triggers protection check."""
    with patch("app.api.routes.actions.SafetyService") as mock_safety_class:
        mock_safety = AsyncMock()
        mock_safety_class.return_value = mock_safety

        with patch("app.api.routes.actions.EC2Service") as mock_ec2_class:
            mock_ec2 = AsyncMock()
            mock_ec2.stop_instances.return_value = {
                "would_stop": ["i-1234567890"],
                "dry_run": True,
            }
            mock_ec2_class.return_value = mock_ec2

            with patch("app.api.routes.actions.AuditService") as mock_audit_class:
                mock_audit = AsyncMock()
                mock_audit_class.return_value = mock_audit

                response = await client.post(
                    "/api/actions/ec2/stop",
                    json={"resource_ids": ["i-1234567890"], "dry_run": True},
                )

                assert response.status_code == 200
                # Verify protection check was called
                mock_safety.check_production_protection.assert_called()


@pytest.mark.asyncio
async def test_ec2_terminate_requires_admin(readonly_client: AsyncClient):
    """Test that EC2 terminate requires admin role."""
    response = await readonly_client.post(
        "/api/actions/ec2/terminate",
        json={"resource_ids": ["i-1234567890"], "dry_run": True},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ecs_scale_action(client: AsyncClient):
    """Test ECS scale action."""
    with patch("app.api.routes.actions.SafetyService") as mock_safety_class:
        mock_safety = AsyncMock()
        mock_safety_class.return_value = mock_safety

        with patch("app.api.routes.actions.ECSService") as mock_ecs_class:
            mock_ecs = AsyncMock()
            mock_ecs.scale_service.return_value = {
                "would_scale": "cluster/service",
                "current_count": 2,
                "desired_count": 4,
                "dry_run": True,
            }
            mock_ecs_class.return_value = mock_ecs

            with patch("app.api.routes.actions.AuditService") as mock_audit_class:
                mock_audit = AsyncMock()
                mock_audit_class.return_value = mock_audit

                response = await client.put(
                    "/api/actions/ecs/scale",
                    json={
                        "resource_ids": ["cluster/service"],
                        "cluster": "cluster",
                        "service": "service",
                        "desired_count": 4,
                        "dry_run": True,
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "dry_run"
                assert data["action"] == "scale"
