"""Redis cache management."""

import json
from datetime import datetime, date
from typing import Any, Optional

import redis.asyncio as redis

from app.config import get_settings


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)

settings = get_settings()

redis_client: Optional[redis.Redis] = None


async def init_cache():
    """Initialize Redis connection."""
    global redis_client
    redis_client = redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )


async def close_cache():
    """Close Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.close()


async def get_cache() -> redis.Redis:
    """Get Redis client instance."""
    if redis_client is None:
        await init_cache()
    return redis_client


class CacheService:
    """Service for caching operations."""

    def __init__(self, client: redis.Redis, prefix: str = "aws_monitor"):
        self.client = client
        self.prefix = prefix
        self.default_ttl = settings.cache_ttl

    def _make_key(self, key: str) -> str:
        """Create prefixed cache key."""
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        value = await self.client.get(self._make_key(key))
        if value:
            return json.loads(value)
        return None

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> None:
        """Set value in cache with optional TTL."""
        await self.client.set(
            self._make_key(key),
            json.dumps(value, cls=DateTimeEncoder),
            ex=ttl or self.default_ttl,
        )

    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        await self.client.delete(self._make_key(key))

    async def delete_pattern(self, pattern: str) -> None:
        """Delete all keys matching pattern."""
        full_pattern = self._make_key(pattern)
        keys = await self.client.keys(full_pattern)
        if keys:
            await self.client.delete(*keys)

    async def invalidate_resources(self, resource_type: Optional[str] = None):
        """Invalidate resource cache."""
        if resource_type:
            await self.delete_pattern(f"resources:{resource_type}:*")
        else:
            await self.delete_pattern("resources:*")
