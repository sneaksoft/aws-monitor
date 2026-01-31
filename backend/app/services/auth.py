"""Authentication service for Cognito integration."""

import json
from typing import Any, Optional

import httpx
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.database import User

settings = get_settings()


class AuthService:
    """Service for authentication with AWS Cognito."""

    def __init__(self):
        self.user_pool_id = settings.cognito_user_pool_id
        self.client_id = settings.cognito_client_id
        self.region = settings.cognito_region
        self._jwks = None

    @property
    def issuer(self) -> str:
        """Get the Cognito issuer URL."""
        return f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"

    @property
    def jwks_url(self) -> str:
        """Get the JWKS URL."""
        return f"{self.issuer}/.well-known/jwks.json"

    async def _get_jwks(self) -> dict:
        """Fetch and cache JWKS from Cognito."""
        if self._jwks is None:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_url)
                response.raise_for_status()
                self._jwks = response.json()
        return self._jwks

    async def verify_token(self, token: str) -> dict[str, Any]:
        """Verify a JWT token from Cognito."""
        if not self.user_pool_id:
            # Development mode - return mock payload
            return {"sub": "dev-user", "email": "dev@example.com"}

        try:
            # Get JWKS
            jwks = await self._get_jwks()

            # Decode header without verification to get key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            # Find matching key
            key = None
            for k in jwks.get("keys", []):
                if k.get("kid") == kid:
                    key = k
                    break

            if not key:
                raise ValueError("Public key not found in JWKS")

            # Verify and decode token
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer,
            )

            return payload

        except JWTError as e:
            raise ValueError(f"Invalid token: {str(e)}")

    async def authenticate(
        self, username: str, password: str
    ) -> dict[str, Any]:
        """Authenticate user with Cognito."""
        if not self.user_pool_id:
            # Development mode - return mock tokens
            return {
                "access_token": "dev-token",
                "expires_in": 3600,
                "sub": "dev-user",
            }

        import aioboto3

        session = aioboto3.Session()
        async with session.client(
            "cognito-idp",
            region_name=self.region,
        ) as client:
            try:
                response = await client.initiate_auth(
                    ClientId=self.client_id,
                    AuthFlow="USER_PASSWORD_AUTH",
                    AuthParameters={
                        "USERNAME": username,
                        "PASSWORD": password,
                    },
                )

                result = response.get("AuthenticationResult", {})
                return {
                    "access_token": result.get("AccessToken"),
                    "refresh_token": result.get("RefreshToken"),
                    "expires_in": result.get("ExpiresIn", 3600),
                    "sub": await self._get_sub_from_token(result.get("AccessToken")),
                }
            except Exception as e:
                raise ValueError(f"Authentication failed: {str(e)}")

    async def _get_sub_from_token(self, token: str) -> str:
        """Extract sub claim from token."""
        payload = await self.verify_token(token)
        return payload.get("sub", "")

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh access token."""
        if not self.user_pool_id:
            return {
                "access_token": "dev-token-refreshed",
                "expires_in": 3600,
            }

        import aioboto3

        session = aioboto3.Session()
        async with session.client(
            "cognito-idp",
            region_name=self.region,
        ) as client:
            response = await client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow="REFRESH_TOKEN_AUTH",
                AuthParameters={
                    "REFRESH_TOKEN": refresh_token,
                },
            )

            result = response.get("AuthenticationResult", {})
            return {
                "access_token": result.get("AccessToken"),
                "expires_in": result.get("ExpiresIn", 3600),
            }

    async def get_user_by_cognito_sub(
        self, db: AsyncSession, cognito_sub: str
    ) -> Optional[User]:
        """Get user by Cognito sub."""
        query = select(User).where(User.cognito_sub == cognito_sub)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_or_create_user(
        self,
        db: AsyncSession,
        cognito_sub: str,
        email: str,
        role: str = "readonly",
    ) -> User:
        """Get existing user or create new one."""
        user = await self.get_user_by_cognito_sub(db, cognito_sub)

        if not user:
            user = User(
                cognito_sub=cognito_sub,
                email=email,
                role=role,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        return user
