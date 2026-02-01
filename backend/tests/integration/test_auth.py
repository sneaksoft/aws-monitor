"""Integration tests for auth endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success_logs_audit(client: AsyncClient):
    """Test that successful login is logged to audit."""
    with patch("app.api.routes.auth.AuthService") as mock_auth_class:
        mock_auth = AsyncMock()
        mock_auth.authenticate.return_value = {
            "sub": "user-123",
            "access_token": "token123",
            "expires_in": 3600,
            "refresh_token": "refresh123",
        }
        mock_auth.get_or_create_user.return_value = AsyncMock(
            id="user-123",
            email="test@example.com",
        )
        mock_auth_class.return_value = mock_auth

        with patch("app.api.routes.auth.AuditService") as mock_audit_class:
            mock_audit = AsyncMock()
            mock_audit_class.return_value = mock_audit

            response = await client.post(
                "/api/auth/login",
                json={"username": "test@example.com", "password": "password123"},
            )

            assert response.status_code == 200

            # Verify audit log was called with success status
            mock_audit.log_action.assert_called_once()
            call_kwargs = mock_audit.log_action.call_args.kwargs
            assert call_kwargs["action"] == "auth:login"
            assert call_kwargs["status"] == "success"
            assert call_kwargs["resource_type"] == "auth"


@pytest.mark.asyncio
async def test_login_failure_logs_audit(client: AsyncClient):
    """Test that failed login attempts are logged to audit."""
    with patch("app.api.routes.auth.AuthService") as mock_auth_class:
        mock_auth = AsyncMock()
        mock_auth.authenticate.side_effect = Exception("Invalid credentials")
        mock_auth_class.return_value = mock_auth

        with patch("app.api.routes.auth.AuditService") as mock_audit_class:
            mock_audit = AsyncMock()
            mock_audit_class.return_value = mock_audit

            response = await client.post(
                "/api/auth/login",
                json={"username": "bad@example.com", "password": "wrongpassword"},
            )

            assert response.status_code == 401

            # Verify audit log was called with failed status
            mock_audit.log_action.assert_called_once()
            call_kwargs = mock_audit.log_action.call_args.kwargs
            assert call_kwargs["action"] == "auth:login"
            assert call_kwargs["status"] == "failed"
            assert call_kwargs["user"] is None  # No user for failed login
            assert "error" in call_kwargs["response_data"]


@pytest.mark.asyncio
async def test_logout_logs_audit(client: AsyncClient):
    """Test that logout is logged to audit."""
    with patch("app.api.routes.auth.AuditService") as mock_audit_class:
        mock_audit = AsyncMock()
        mock_audit_class.return_value = mock_audit

        response = await client.post("/api/auth/logout")

        assert response.status_code == 200

        # Verify audit log was called
        mock_audit.log_action.assert_called_once()
        call_kwargs = mock_audit.log_action.call_args.kwargs
        assert call_kwargs["action"] == "auth:logout"
        assert call_kwargs["status"] == "success"


@pytest.mark.asyncio
async def test_refresh_token_success_logs_audit(client: AsyncClient):
    """Test that successful token refresh is logged to audit."""
    with patch("app.api.routes.auth.AuthService") as mock_auth_class:
        mock_auth = AsyncMock()
        mock_auth.refresh_token.return_value = {
            "access_token": "newtoken123",
            "expires_in": 3600,
        }
        mock_auth_class.return_value = mock_auth

        with patch("app.api.routes.auth.AuditService") as mock_audit_class:
            mock_audit = AsyncMock()
            mock_audit_class.return_value = mock_audit

            response = await client.post(
                "/api/auth/refresh",
                params={"refresh_token": "valid_refresh_token"},
            )

            assert response.status_code == 200

            # Verify audit log was called
            mock_audit.log_action.assert_called_once()
            call_kwargs = mock_audit.log_action.call_args.kwargs
            assert call_kwargs["action"] == "auth:refresh"
            assert call_kwargs["status"] == "success"


@pytest.mark.asyncio
async def test_refresh_token_failure_logs_audit(client: AsyncClient):
    """Test that failed token refresh is logged to audit."""
    with patch("app.api.routes.auth.AuthService") as mock_auth_class:
        mock_auth = AsyncMock()
        mock_auth.refresh_token.side_effect = Exception("Token expired")
        mock_auth_class.return_value = mock_auth

        with patch("app.api.routes.auth.AuditService") as mock_audit_class:
            mock_audit = AsyncMock()
            mock_audit_class.return_value = mock_audit

            response = await client.post(
                "/api/auth/refresh",
                params={"refresh_token": "invalid_token"},
            )

            assert response.status_code == 401

            # Verify audit log was called with failed status
            mock_audit.log_action.assert_called_once()
            call_kwargs = mock_audit.log_action.call_args.kwargs
            assert call_kwargs["action"] == "auth:refresh"
            assert call_kwargs["status"] == "failed"
            assert "error" in call_kwargs["response_data"]
