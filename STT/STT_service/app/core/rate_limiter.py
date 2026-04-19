"""
STT Service - Redis-based Rate Limiter

Implements a sliding window counter rate limiter using Redis.
Each API key gets its own rate limit window (default: 100 requests/minute).
"""

from datetime import datetime
from typing import Optional

import redis.asyncio as aioredis

from app.config import get_settings
from app.core.exceptions import RateLimitExceededError
from app.core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Redis connection pool (initialized lazily)
_redis_pool: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Get or create the Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
        )
    return _redis_pool


async def close_redis() -> None:
    """Close the Redis connection pool on shutdown."""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None


async def check_rate_limit(
    key_id: str,
    limit: int = None,
    window_seconds: int = 60,
) -> dict:
    """
    Check if a request is within the rate limit for a given API key.
    
    Uses Redis sorted sets with timestamps as scores for a sliding window.
    
    Args:
        key_id: The API key ID to check.
        limit: Max requests per window (default from settings).
        window_seconds: Window size in seconds (default: 60).
    
    Returns:
        dict with remaining quota and reset time.
    
    Raises:
        RateLimitExceededError: If the limit is exceeded.
    """
    if limit is None:
        limit = settings.rate_limit_per_minute

    r = await get_redis()
    redis_key = f"rate_limit:{key_id}"
    now = datetime.utcnow().timestamp()
    window_start = now - window_seconds

    # Use a Redis pipeline for atomic operations
    pipe = r.pipeline()

    # Remove expired entries (outside the sliding window)
    pipe.zremrangebyscore(redis_key, "-inf", window_start)

    # Count current entries in the window
    pipe.zcard(redis_key)

    # Add the current request
    pipe.zadd(redis_key, {f"{now}": now})

    # Set TTL so Redis auto-cleans old keys
    pipe.expire(redis_key, window_seconds + 10)

    results = await pipe.execute()
    current_count = results[1]  # zcard result

    if current_count >= limit:
        logger.warning(
            "rate_limit_exceeded",
            key_id=key_id,
            current=current_count,
            limit=limit,
        )
        raise RateLimitExceededError(retry_after=window_seconds)

    remaining = limit - current_count - 1  # -1 for current request
    reset_at = int(now + window_seconds)

    logger.debug(
        "rate_limit_check",
        key_id=key_id,
        remaining=remaining,
        limit=limit,
    )

    return {
        "limit": limit,
        "remaining": max(0, remaining),
        "reset_at": reset_at,
    }
