"""email verification code Redis store (auth context)"""
from __future__ import annotations

from typing import Optional, Tuple

from shared.infrastructure.di.redis_session import get_redis


def _code_key(purpose: str, email: str) -> str:
    return f"email_code:{purpose}:{email}"


def rate_limit_key(window: str, purpose: str, email: str) -> str:
    return f"rl:email_code:{window}:{purpose}:{email}"


async def store_code(code: str, ttl_seconds: int, purpose: str, email: str) -> None:
    """store 6-digit code (plaintext, TTL=ttl_seconds)"""
    redis = await get_redis()
    await redis.set(_code_key(purpose, email), code, ex=ttl_seconds)


async def get_code(purpose: str, email: str) -> Optional[str]:
    """get code (don't delete; caller decides when to delete)"""
    redis = await get_redis()
    return await redis.get(_code_key(purpose, email))


async def delete_code(purpose: str, email: str) -> None:
    """delete code (email-send-failure rollback / after pass-and-destroy)"""
    redis = await get_redis()
    await redis.delete(_code_key(purpose, email))


async def check_rate_limit(
    window: str,
    purpose: str,
    email: str,
    max_count: int,
    window_seconds: int,
) -> Tuple[bool, int]:
    """email code rate limit (count every send)

    Returns: (allowed, remaining)
    """
    redis = await get_redis()
    key = rate_limit_key(window, purpose, email)
    async with redis.pipeline(transaction=True) as pipe:
        await pipe.incr(key)
        await pipe.expire(key, window_seconds)
        count, _ = await pipe.execute()
    remaining = max(0, max_count - count)
    return count <= max_count, remaining


__all__ = [
    "check_rate_limit",
    "delete_code",
    "get_code",
    "rate_limit_key",
    "store_code",
]
