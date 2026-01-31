"""AWS account management endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import RequireAdmin
from app.models.database import AWSAccount
from app.models.schemas import AWSAccountCreate, AWSAccountResponse

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
):
    """Add a new AWS account (admin only)."""
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
):
    """Update AWS account (admin only)."""
    query = select(AWSAccount).where(AWSAccount.id == account_id)
    result = await db.execute(query)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    for key, value in account_update.model_dump().items():
        setattr(account, key, value)

    await db.commit()
    await db.refresh(account)

    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: UUID,
    user: RequireAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete AWS account (admin only)."""
    query = select(AWSAccount).where(AWSAccount.id == account_id)
    result = await db.execute(query)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    await db.delete(account)
    await db.commit()


@router.post("/{account_id}/verify")
async def verify_account(
    account_id: UUID,
    user: RequireAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Verify AWS account access by testing AssumeRole (admin only)."""
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
        return {"status": "verified", "message": "Successfully assumed role"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to assume role: {str(e)}",
        )
