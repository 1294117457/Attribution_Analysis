"""Redis 缓存工具类

提供业务无关的 Redis 操作(限流 / 设置 TTL KV / 集合 / 黑名单 等)。

参考: iddata/idbackend 的 src/infra/redis.py RedisCache
"""
from __future__ import annotations

import uuid
from typing import Optional

from redis.asyncio import Redis

from infrastructure.adapter.cache.redis_client import get_redis
from infrastructure.config.settings import get_settings


def _new_redis() -> Redis:
    """同步取出缓存好的 Redis 连接(供 RedisCache 实例化时使用)。"""
    import asyncio

    return asyncio.get_event_loop().run_until_complete(get_redis())


class RedisCache:
    """Redis 缓存工具(对外暴露 async API)"""

    def __init__(self, redis: Redis):
        self.redis = redis

    # ── KV ──────────────────────────────────────────────────────────

    async def get(self, key: str) -> Optional[str]:
        return await self.redis.get(key)

    async def set(self, key: str, value: str, expire: int = 3600) -> bool:
        return await self.redis.set(key, value, ex=expire)

    async def delete(self, *keys: str) -> int:
        return await self.redis.delete(*keys)

    async def exists(self, key: str) -> bool:
        return await self.redis.exists(key) > 0

    async def incr(self, key: str) -> int:
        return await self.redis.incr(key)

    async def expire(self, key: str, seconds: int) -> bool:
        return await self.redis.expire(key, seconds)

    # ── 限流(increment + expire 原子)──────────────────────────────

    async def rate_limit(
        self,
        key: str,
        max_count: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """基于 Redis 的滑动窗口式限流(每窗口都重置 expire)。

        返回 (allowed: bool, remaining: int):
        - allowed   当前计数 ≤ max_count 时,True
        - remaining 剩余可用次数(0 表示已用尽)
        """
        async with self.redis.pipeline(transaction=True) as pipe:
            await pipe.incr(key)
            await pipe.expire(key, window_seconds)
            count, _ = await pipe.execute()
        remaining = max(0, max_count - count)
        return count <= max_count, remaining

    # ── 集合 ───────────────────────────────────────────────────────

    async def sadd(self, key: str, *members: str) -> int:
        return await self.redis.sadd(key, *members)

    async def smembers(self, key: str) -> set[str]:
        return await self.redis.smembers(key)

    async def srem(self, key: str, *members: str) -> int:
        return await self.redis.srem(key, *members)

    # ── 邮箱验证码专用 ────────────────────────────────────────────

    async def store_email_code(self, code: str, ttl_seconds: int, *key_parts: str) -> None:
        """写 6 位数字码(key 自动拼),到时自动过期。"""
        await self.redis.set(self._email_code_key(*key_parts), code, ex=ttl_seconds)

    async def get_email_code(self, *key_parts: str) -> Optional[str]:
        return await self.redis.get(self._email_code_key(*key_parts))

    async def delete_email_code(self, *key_parts: str) -> None:
        await self.redis.delete(self._email_code_key(*key_parts))

    @staticmethod
    def _email_code_key(purpose: str, email: str) -> str:
        return f"email_code:{purpose}:{email}"

    @staticmethod
    def email_rate_limit_key(window: str, purpose: str, email: str) -> str:
        """限频键:rl:email_code:{1m|1h}:{purpose}:{email}"""
        return f"rl:email_code:{window}:{purpose}:{email}"

    # ── Refresh Token 黑名单(带 TTL)──────────────────────────────

    async def revoke_refresh_token(self, jti: str, ttl_seconds: int) -> None:
        """撤销 refresh token(jti 加入黑名单,TTL 与 refresh 剩余有效期一致)。"""
        await self.redis.set(f"revoked:{jti}", "1", ex=ttl_seconds)

    async def is_refresh_token_revoked(self, jti: str) -> bool:
        return await self.redis.exists(f"revoked:{jti}") > 0

    async def revoke_all_user_refresh_tokens(self, user_id: int) -> int:
        """撤销该用户所有 refresh tokens(改密 / 改密码 / 封号时调用)。"""
        key = f"user_refresh_tokens:{user_id}"
        jtis = await self.redis.smembers(key)
        if not jtis:
            return 0
        # 用 pipeline 一次性写多个 key,效率高
        async with self.redis.pipeline(transaction=True) as pipe:
            for jti in jtis:
                # 用 7 天兜底 TTL(idbackend 用的;我们 refresh 期限也是 7 天)
                pipe.set(f"revoked:{jti}", "1", ex=7 * 24 * 60 * 60)
            pipe.delete(key)
            await pipe.execute()
        return len(jtis)


async def get_cache() -> RedisCache:
    """获取 RedisCache 实例(供 FastAPI Depends / service 注入)。"""
    return RedisCache(await get_redis())