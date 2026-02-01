"""Integration tests for account management endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_account_logs_audit(client: AsyncClient, db_session):
    """Test that account creation is logged to audit."""
    with patch("app.api.routes.accounts.AuditService") as mock_audit_class:
        mock_audit = AsyncMock()
        mock_audit_class.return_value = mock_audit

        response = await client.post(
            "/api/accounts",
            json={
                "account_id": "123456789012",
                "account_name": "Test Account",
                "role_arn": "arn:aws:iam::123456789012:role/TestRole",
            },
        )

        assert response.status_code == 201

        # Verify audit log was called
        mock_audit.log_action.assert_called_once()
        call_kwargs = mock_audit.log_action.call_args.kwargs
        assert call_kwargs["action"] == "account:create"
        assert call_kwargs["status"] == "success"
        assert call_kwargs["resource_type"] == "aws_account"
        assert "account_id" in call_kwargs["request_data"]
        assert "role_arn" in call_kwargs["request_data"]


@pytest.mark.asyncio
async def test_update_account_logs_before_after_values(client: AsyncClient, db_session):
    """Test that account update logs before/after values."""
    # First create an account
    with patch("app.api.routes.accounts.AuditService") as mock_audit_class:
        mock_audit = AsyncMock()
        mock_audit_class.return_value = mock_audit

        create_response = await client.post(
            "/api/accounts",
            json={
                "account_id": "123456789013",
                "account_name": "Original Name",
                "role_arn": "arn:aws:iam::123456789013:role/OriginalRole",
            },
        )
        assert create_response.status_code == 201
        account_uuid = create_response.json()["id"]

    # Now update it
    with patch("app.api.routes.accounts.AuditService") as mock_audit_class:
        mock_audit = AsyncMock()
        mock_audit_class.return_value = mock_audit

        update_response = await client.put(
            f"/api/accounts/{account_uuid}",
            json={
                "account_id": "123456789013",
                "account_name": "Updated Name",
                "role_arn": "arn:aws:iam::123456789013:role/UpdatedRole",
            },
        )

        assert update_response.status_code == 200

        # Verify audit log was called with before/after values
        mock_audit.log_action.assert_called_once()
        call_kwargs = mock_audit.log_action.call_args.kwargs
        assert call_kwargs["action"] == "account:update"
        assert call_kwargs["status"] == "success"
        assert "before" in call_kwargs["request_data"]
        assert "after" in call_kwargs["request_data"]
        assert call_kwargs["request_data"]["before"]["account_name"] == "Original Name"
        assert call_kwargs["request_data"]["after"]["account_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_delete_account_logs_audit(client: AsyncClient, db_session):
    """Test that account deletion is logged to audit."""
    # First create an account
    with patch("app.api.routes.accounts.AuditService") as mock_audit_class:
        mock_audit = AsyncMock()
        mock_audit_class.return_value = mock_audit

        create_response = await client.post(
            "/api/accounts",
            json={
                "account_id": "123456789014",
                "account_name": "To Be Deleted",
                "role_arn": "arn:aws:iam::123456789014:role/DeleteMe",
            },
        )
        assert create_response.status_code == 201
        account_uuid = create_response.json()["id"]

    # Now delete it
    with patch("app.api.routes.accounts.AuditService") as mock_audit_class:
        mock_audit = AsyncMock()
        mock_audit_class.return_value = mock_audit

        delete_response = await client.delete(f"/api/accounts/{account_uuid}")

        assert delete_response.status_code == 204

        # Verify audit log was called
        mock_audit.log_action.assert_called_once()
        call_kwargs = mock_audit.log_action.call_args.kwargs
        assert call_kwargs["action"] == "account:delete"
        assert call_kwargs["status"] == "success"
        assert call_kwargs["request_data"]["account_id"] == "123456789014"


@pytest.mark.asyncio
async def test_verify_account_success_logs_audit(client: AsyncClient, db_session):
    """Test that successful account verification is logged to audit."""
    # First create an account
    with patch("app.api.routes.accounts.AuditService") as mock_audit_class:
        mock_audit = AsyncMock()
        mock_audit_class.return_value = mock_audit

        create_response = await client.post(
            "/api/accounts",
            json={
                "account_id": "123456789015",
                "account_name": "Verify Me",
                "role_arn": "arn:aws:iam::123456789015:role/VerifyRole",
            },
        )
        assert create_response.status_code == 201
        account_uuid = create_response.json()["id"]

    # Now verify it
    with patch("app.api.routes.accounts.AuditService") as mock_audit_class:
        mock_audit = AsyncMock()
        mock_audit_class.return_value = mock_audit

        with patch("app.services.aws.base.AWSBaseService") as mock_aws_class:
            mock_aws = AsyncMock()
            mock_aws_class.return_value = mock_aws

            verify_response = await client.post(f"/api/accounts/{account_uuid}/verify")

            assert verify_response.status_code == 200

            # Verify audit log was called
            mock_audit.log_action.assert_called_once()
            call_kwargs = mock_audit.log_action.call_args.kwargs
            assert call_kwargs["action"] == "account:verify"
            assert call_kwargs["status"] == "success"


@pytest.mark.asyncio
async def test_verify_account_failure_logs_audit(client: AsyncClient, db_session):
    """Test that failed account verification is logged to audit."""
    # First create an account
    with patch("app.api.routes.accounts.AuditService") as mock_audit_class:
        mock_audit = AsyncMock()
        mock_audit_class.return_value = mock_audit

        create_response = await client.post(
            "/api/accounts",
            json={
                "account_id": "123456789016",
                "account_name": "Fail Verify",
                "role_arn": "arn:aws:iam::123456789016:role/BadRole",
            },
        )
        assert create_response.status_code == 201
        account_uuid = create_response.json()["id"]

    # Now try to verify it (will fail)
    with patch("app.api.routes.accounts.AuditService") as mock_audit_class:
        mock_audit = AsyncMock()
        mock_audit_class.return_value = mock_audit

        with patch("app.services.aws.base.AWSBaseService") as mock_aws_class:
            mock_aws = AsyncMock()
            mock_aws.verify_role_access.side_effect = Exception("Access denied")
            mock_aws_class.return_value = mock_aws

            verify_response = await client.post(f"/api/accounts/{account_uuid}/verify")

            assert verify_response.status_code == 400

            # Verify audit log was called with failed status
            mock_audit.log_action.assert_called_once()
            call_kwargs = mock_audit.log_action.call_args.kwargs
            assert call_kwargs["action"] == "account:verify"
            assert call_kwargs["status"] == "failed"
            assert "error" in call_kwargs["response_data"]
