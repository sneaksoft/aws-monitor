"""FastAPI dependency injection."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.cache import get_cache, CacheService
from app.models.database import User
from app.services.auth import AuthService

security = HTTPBearer()


async def get_cache_service() -> CacheService:
    """Get cache service instance."""
    client = await get_cache()
    return CacheService(client)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Validate JWT and return current user."""
    auth_service = AuthService()
    token = credentials.credentials

    try:
        payload = await auth_service.verify_token(token)
        user = await auth_service.get_user_by_cognito_sub(db, payload["sub"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


def require_role(*roles: str):
    """Dependency factory for role-based access control."""

    async def role_checker(
        user: Annotated[User, Depends(get_current_user)]
    ) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' not authorized. Required: {roles}",
            )
        return user

    return role_checker


# Common role dependencies
RequireAdmin = Annotated[User, Depends(require_role("admin"))]
RequireOperator = Annotated[User, Depends(require_role("admin", "operator"))]
RequireReadonly = Annotated[User, Depends(require_role("admin", "operator", "readonly"))]
