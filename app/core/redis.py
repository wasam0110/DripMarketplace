"""
app/core/redis.py
─────────────────
Redis connection pool for rate limiting, task queuing, and caching.

Uses hiredis parser for ~10x faster response parsing.
"""

from __future__ import annotations

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Module-level singleton
_redis: Redis | None = None


async def init_redis() -> None:
    """Create the Redis connection pool. Called at app startup."""
    global _redis
    _redis = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=20,
        socket_timeout=5,
        socket_connect_timeout=5,
        retry_on_timeout=True,
    )
    # Verify connection
    try:
        await _redis.ping()
        logger.info("redis.connected")
    except Exception as exc:
        logger.error("redis.connection_failed", error=str(exc))
        raise


async def close_redis() -> None:
    """Close the Redis connection pool. Called at app shutdown."""
    global _redis
    if _redis:
        await _redis.aclose()
        logger.info("redis.disconnected")
        _redis = None


def get_redis() -> Redis:
    """Return the module-level Redis client. Raises if not initialised."""
    if _redis is None:
        raise RuntimeError("Redis not initialised. Call init_redis() first.")
    return _redis


# ── Key namespace helpers ──────────────────────────────────────────────────────

class RedisKeys:
    """
    Centralised Redis key naming.
    All keys follow: drip:{namespace}:{identifier}
    """

    @staticmethod
    def rate_limit(key: str) -> str:
        return f"drip:rl:{key}"

    @staticmethod
    def jwt_blocklist(jti: str) -> str:
        return f"drip:jwt:block:{jti}"

    @staticmethod
    def email_verify_token(token: str) -> str:
        return f"drip:email:verify:{token}"

    @staticmethod
    def password_reset_token(token: str) -> str:
        return f"drip:pwd:reset:{token}"

    @staticmethod
    def product_cache(product_id: str) -> str:
        return f"drip:cache:product:{product_id}"

    @staticmethod
    def catalogue_cache(filter_hash: str) -> str:
        return f"drip:cache:cat:{filter_hash}"

    @staticmethod
    def seller_dashboard_cache(seller_id: str, period: str) -> str:
        return f"drip:cache:dash:{seller_id}:{period}"

    @staticmethod
    def cod_timer(order_id: str) -> str:
        return f"drip:cod:timer:{order_id}"

    @staticmethod
    def login_attempts(ip: str) -> str:
        return f"drip:login:attempts:{ip}"


# ── Cache helpers ─────────────────────────────────────────────────────────────

async def cache_get(key: str) -> str | None:
    """Get a cached value. Returns None on miss or Redis error."""
    try:
        return await get_redis().get(key)
    except Exception as exc:
        logger.warning("redis.cache_get_failed", key=key, error=str(exc))
        return None


async def cache_set(key: str, value: str, ttl_seconds: int) -> bool:
    """Set a cache value with TTL. Returns False on error (non-fatal)."""
    try:
        await get_redis().setex(key, ttl_seconds, value)
        return True
    except Exception as exc:
        logger.warning("redis.cache_set_failed", key=key, error=str(exc))
        return False


async def cache_delete(key: str) -> None:
    """Invalidate a cache key. Silently ignores errors."""
    try:
        await get_redis().delete(key)
    except Exception as exc:
        logger.warning("redis.cache_delete_failed", key=key, error=str(exc))


async def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern. Returns count of deleted keys."""
    try:
        redis = get_redis()
        keys = await redis.keys(pattern)
        if keys:
            return await redis.delete(*keys)
        return 0
    except Exception as exc:
        logger.warning("redis.cache_delete_pattern_failed", pattern=pattern, error=str(exc))
        return 0