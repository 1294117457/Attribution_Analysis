"""Refresh Token blacklist (auth context, Redis impl)

Data model:
  - revoked:{jti}                    string "1", TTL = refresh remaining TTL
  - user_refresh_tokens:{user_id}    set of jti, TTL = 7 days (sync refresh period)

Business flow:
  - register(jti, user_id)            login success -> add jti to user active set
  - is_active(jti)                    pre-check, not revoked -> True
  - revoke(jti, ttl)                  logout / change password -> blacklist
  - revoke_all_for_user(user_id)      change password / ban -> revoke all
"""
from __future__ import annotations

import logging
from typing import Set

# ★ 全局单例直连，无需 Depends 注入
from shared.infrastructure.connection.redis_client import redis as redis_client

logger = logging.getLogger(__name__)

# Set key TTL padding: 7 days, ensure expired set auto-released
_SET_TTL_SECONDS = 7 * 24 * 60 * 60
# revoke jti TTL: 7 days
_REVOKE_TTL_SECONDS = 7 * 24 * 60 * 60


def _user_set_key(user_id: int) -> str:
    return f"user_refresh_tokens:{user_id}"


def _revoked_key(jti: str) -> str:
    return f"revoked:{jti}"


async def register(user_id: int, jti: str, expires_in_seconds: int) -> None:
    """register a new refresh token: add jti to user's active set

    Args:
        user_id: user ID
        jti: refresh token unique id (JWT claim)
        expires_in_seconds: refresh TTL, set TTL sync with it
    """
    set_key = _user_set_key(user_id)
    await redis_client.sadd(set_key, jti)
    await redis_client.expire(set_key, expires_in_seconds)


async def is_active(jti: str) -> bool:
    """not revoked -> True. revoked / key not exist -> False."""
    return (await redis_client.exists(_revoked_key(jti))) == 0


async def revoke(jti: str, expires_in_seconds: int) -> None:
    """revoke single jti (write blacklist). TTL = refresh remaining TTL."""
    await redis_client.set(_revoked_key(jti), "1", ex=expires_in_seconds)


async def revoke_all_for_user(user_id: int) -> int:
    """revoke all active refresh tokens of the user (change password / ban)

    Returns:
        count of revoked jti
    """
    set_key = _user_set_key(user_id)
    jtis: Set[str] = await redis_client.smembers(set_key)
    if not jtis:
        return 0
    # use pipeline to write multiple keys in one go, high efficiency
    async with redis_client.pipeline(transaction=True) as pipe:
        for jti in jtis:
            pipe.set(_revoked_key(jti), "1", ex=_REVOKE_TTL_SECONDS)
        pipe.delete(set_key)
        await pipe.execute()
    return len(jtis)


__all__ = [
    "is_active",
    "register",
    "revoke",
    "revoke_all_for_user",
]
