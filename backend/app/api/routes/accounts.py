"""AWS account management endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import RequireAdmin
from app.models.database import AWSAccount
from app.models.schemas import AWSAccountCreate, AWSAccountResponse
from app.services.audit import AuditService

router = APIRouter()


@router.get("", response_model=list[AWSAccountResponse])
async def list_accounts(
    user: RequireAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List configured AWS accounts (admin only)."""
    query = select(AWSAccount).order_by(AWSAccount.account_name)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=AWSAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    account: AWSAccountCreate,
    user: RequireAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
    http_request: Request,
):
    """Add a new AWS account (admin only)."""
    audit = AuditService()

    # Check if account already exists
    existing = await db.execute(
        select(AWSAccount).where(AWSAccount.account_id == account.account_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Account {account.account_id} already exists",
        )

    db_account = AWSAccount(**account.model_dump())
    db.add(db_account)
    await db.commit()
    await db.refresh(db_account)

    # Log account creation
    await audit.log_action(
        user=user,
        action="account:create",
        resource_type="aws_account",
        resource_ids=[account.account_id],
        request=http_request,
        status="success",
        request_data={
            "account_id": account.account_id,
            "account_name": account.account_name,
            "role_arn": account.role_arn,
        },
    )

    return db_account


@router.get("/{account_id}", response_model=AWSAccountResponse)
async def get_account(
    account_id: UUID,
    user: RequireAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get AWS account details (admin only)."""
    query = select(AWSAccount).where(AWSAccount.id == account_id)
    result = await db.execute(query)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    return account


@router.put("/{account_id}", response_model=AWSAccountResponse)
async def update_account(
    account_id: UUID,
    account_update: AWSAccountCreate,
    user: RequireAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
    http_request: Request,
):
    """Update AWS account (admin only)."""
    audit = AuditService()

    query = select(AWSAccount).where(AWSAccount.id == account_id)
    result = await db.execute(query)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    # Capture before values for audit
    before_values = {
        "account_id": account.account_id,
        "account_name": account.account_name,
        "role_arn": account.role_arn,
    }

    for key, value in account_update.model_dump().items():
        setattr(account, key, value)

    await db.commit()
    await db.refresh(account)

    # Capture after values for audit
    after_values = {
        "account_id": account.account_id,
        "account_name": account.account_name,
        "role_arn": account.role_arn,
    }

    # Log account update with before/after values
    await audit.log_action(
        user=user,
        action="account:update",
        resource_type="aws_account",
        resource_ids=[account.account_id],
        request=http_request,
        status="success",
        request_data={"before": before_values, "after": after_values},
    )

    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: UUID,
    user: RequireAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
    http_request: Request,
):
    """Delete AWS account (admin only)."""
    audit = AuditService()

    query = select(AWSAccount).where(AWSAccount.id == account_id)
    result = await db.execute(query)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    # Capture account details before deletion for audit
    deleted_account_data = {
        "account_id": account.account_id,
        "account_name": account.account_name,
        "role_arn": account.role_arn,
    }

    await db.delete(account)
    await db.commit()

    # Log account deletion
    await audit.log_action(
        user=user,
        action="account:delete",
        resource_type="aws_account",
        resource_ids=[deleted_account_data["account_id"]],
        request=http_request,
        status="success",
        request_data=deleted_account_data,
    )


@router.post("/{account_id}/verify")
async def verify_account(
    account_id: UUID,
    user: RequireAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
    http_request: Request,
):
    """Verify AWS account access by testing AssumeRole (admin only)."""
    audit = AuditService()

    query = select(AWSAccount).where(AWSAccount.id == account_id)
    result = await db.execute(query)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    # Test AssumeRole
    from app.services.aws.base import AWSBaseService

    try:
        aws_service = AWSBaseService()
        await aws_service.verify_role_access(
            role_arn=account.role_arn,
            external_id=account.external_id,
        )

        # Log successful verification
        await audit.log_action(
            user=user,
            action="account:verify",
            resource_type="aws_account",
            resource_ids=[account.account_id],
            request=http_request,
            status="success",
            request_data={
                "account_id": account.account_id,
                "role_arn": account.role_arn,
            },
        )

        return {"status": "verified", "message": "Successfully assumed role"}
    except Exception as e:
        # Log failed verification
        await audit.log_action(
            user=user,
            action="account:verify",
            resource_type="aws_account",
            resource_ids=[account.account_id],
            request=http_request,
            status="failed",
            request_data={
                "account_id": account.account_id,
                "role_arn": account.role_arn,
            },
            response_data={"error": str(e), "error_type": type(e).__name__},
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to assume role: {str(e)}",
        )
