"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.database import User
from app.models.schemas import UserResponse, LoginRequest, TokenResponse
from app.services.auth import AuthService
from app.services.audit import AuditService

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    http_request: Request,
):
    """Authenticate user with Cognito."""
    auth_service = AuthService()
    audit = AuditService()

    try:
        result = await auth_service.authenticate(
            request.username, request.password
        )

        # Ensure user exists in database
        user = await auth_service.get_or_create_user(
            db,
            cognito_sub=result["sub"],
            email=request.username,
        )

        # Log successful login
        await audit.log_action(
            user=user,
            action="auth:login",
            resource_type="auth",
            resource_ids=[request.username],
            request=http_request,
            status="success",
            request_data={"username": request.username},
        )

        return TokenResponse(
            access_token=result["access_token"],
            expires_in=result["expires_in"],
            refresh_token=result.get("refresh_token"),
        )
    except Exception as e:
        # Log failed login attempt
        await audit.log_action(
            user=None,
            action="auth:login",
            resource_type="auth",
            resource_ids=[request.username],
            request=http_request,
            status="failed",
            request_data={"username": request.username},
            response_data={"error": str(e), "error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str, http_request: Request):
    """Refresh access token."""
    auth_service = AuthService()
    audit = AuditService()

    try:
        result = await auth_service.refresh_token(refresh_token)

        # Log successful token refresh (user unknown from refresh token)
        await audit.log_action(
            user=None,
            action="auth:refresh",
            resource_type="auth",
            resource_ids=["token"],
            request=http_request,
            status="success",
        )

        return TokenResponse(
            access_token=result["access_token"],
            expires_in=result["expires_in"],
        )
    except Exception as e:
        # Log failed token refresh
        await audit.log_action(
            user=None,
            action="auth:refresh",
            resource_type="auth",
            resource_ids=["token"],
            request=http_request,
            status="failed",
            response_data={"error": str(e), "error_type": type(e).__name__},
        )
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
    http_request: Request,
):
    """Logout user (client should discard tokens)."""
    audit = AuditService()

    # Log logout event
    await audit.log_action(
        user=user,
        action="auth:logout",
        resource_type="auth",
        resource_ids=[user.email],
        request=http_request,
        status="success",
    )

    # Cognito tokens are stateless, logout is client-side
    return {"status": "logged_out"}
