"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.database import User
from app.models.schemas import UserResponse, LoginRequest, TokenResponse
from app.services.auth import AuthService

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Authenticate user with Cognito."""
    auth_service = AuthService()
    try:
        result = await auth_service.authenticate(
            request.username, request.password
        )

        # Ensure user exists in database
        await auth_service.get_or_create_user(
            db,
            cognito_sub=result["sub"],
            email=request.username,
        )

        return TokenResponse(
            access_token=result["access_token"],
            expires_in=result["expires_in"],
            refresh_token=result.get("refresh_token"),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    """Refresh access token."""
    auth_service = AuthService()
    try:
        result = await auth_service.refresh_token(refresh_token)
        return TokenResponse(
            access_token=result["access_token"],
            expires_in=result["expires_in"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: Annotated[User, Depends(get_current_user)],
):
    """Get current authenticated user info."""
    return user


@router.post("/logout")
async def logout(
    user: Annotated[User, Depends(get_current_user)],
):
    """Logout user (client should discard tokens)."""
    # Cognito tokens are stateless, logout is client-side
    return {"status": "logged_out"}
