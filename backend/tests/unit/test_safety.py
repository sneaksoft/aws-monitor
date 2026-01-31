"""Tests for safety service."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from app.services.safety import SafetyService


@pytest.fixture
def safety_service():
    """Create safety service instance."""
    service = SafetyService()
    service.protected_tags = ["production", "prod", "critical"]
    service.admin_override_code = "admin123"
    return service


class TestSafetyService:
    """Tests for SafetyService."""

    @pytest.mark.asyncio
    async def test_check_production_protection_allowed(self, safety_service):
        """Test that non-production resources pass protection check."""
        with patch.object(
            safety_service, "_get_resource_tags", return_value={"Environment": "dev"}
        ):
            # Should not raise
            await safety_service.check_production_protection(
                resource_type="ec2",
                resource_id="i-1234567890",
            )

    @pytest.mark.asyncio
    async def test_check_production_protection_blocked(self, safety_service):
        """Test that production resources are blocked without override."""
        with patch.object(
            safety_service,
            "_get_resource_tags",
            return_value={"Environment": "production"},
        ):
            with pytest.raises(HTTPException) as exc_info:
                await safety_service.check_production_protection(
                    resource_type="ec2",
                    resource_id="i-1234567890",
                )

            assert exc_info.value.status_code == 403
            assert "production" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_check_production_protection_with_override(self, safety_service):
        """Test that production resources can be accessed with override code."""
        with patch.object(
            safety_service,
            "_get_resource_tags",
            return_value={"Environment": "production"},
        ):
            # Should not raise with correct override code
            await safety_service.check_production_protection(
                resource_type="ec2",
                resource_id="i-1234567890",
                override_code="admin123",
            )

    @pytest.mark.asyncio
    async def test_check_production_protection_wrong_override(self, safety_service):
        """Test that wrong override code is rejected."""
        with patch.object(
            safety_service,
            "_get_resource_tags",
            return_value={"Environment": "production"},
        ):
            with pytest.raises(HTTPException):
                await safety_service.check_production_protection(
                    resource_type="ec2",
                    resource_id="i-1234567890",
                    override_code="wrong-code",
                )

    @pytest.mark.asyncio
    async def test_check_protected_tag(self, safety_service):
        """Test that Protected tag blocks modification."""
        with patch.object(
            safety_service, "_get_resource_tags", return_value={"Protected": "true"}
        ):
            with pytest.raises(HTTPException):
                await safety_service.check_production_protection(
                    resource_type="ec2",
                    resource_id="i-1234567890",
                )

    def test_validate_action_admin_only(self, safety_service):
        """Test that admin-only actions are restricted."""
        assert safety_service.validate_action("ec2:terminate", "admin") is True
        assert safety_service.validate_action("ec2:terminate", "operator") is False
        assert safety_service.validate_action("ec2:terminate", "readonly") is False

    def test_validate_action_operator(self, safety_service):
        """Test that operator actions are allowed for operators."""
        assert safety_service.validate_action("ec2:start", "admin") is True
        assert safety_service.validate_action("ec2:start", "operator") is True
        assert safety_service.validate_action("ec2:start", "readonly") is False
