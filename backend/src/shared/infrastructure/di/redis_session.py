"""Redis 客户端依赖注入工厂

仅负责：返回全局 aioredis.Redis 单例（事件循环内 lazy init）。

**不创建** 客户端 —— 构造在 `shared.infrastructure.connection.redis_client._build_client`。
**不包含** 业务缓存逻辑 —— 那些在各 context 的 `infrastructure/cache/`。

使用示例：
    from shared.infrastructure.di.redis_session import get_redis
    client = await get_redis()
    await client.set("key", "value", ex=60)
"""
from __future__ import annotations

import asyncio
import logging

import redis.asyncio as aioredis

from shared.infrastructure.connection.redis_client import _build_client

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None
_init_lock: asyncio.Lock | None = None


async def get_redis() -> aioredis.Redis:
    """获取全局 Redis 单例（事件循环内 lazy 初始化）"""
    global _redis, _init_lock
    if _redis is None:
        if _init_lock is None:
            _init_lock = asyncio.Lock()
        async with _init_lock:
            if _redis is None:  # double-check
                _redis = _build_client()
                logger.info("Redis 客户端初始化完成")
    return _redis


async def close_redis() -> None:
    """关闭全局 Redis 客户端（lifespan 关闭阶段调用）"""
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None


__all__ = ["get_redis", "close_redis"]
