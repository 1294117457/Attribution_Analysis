"""Redis 全局单例客户端。

直接 import 即用，无需 Depends注入：
    from shared.infrastructure.connection.redis_client import redis as redis_client
    await redis_client.hset("k", mapping={...})

设计：
    - 模块级单例 `redis`（连接池复用 + 进程级一致）
    - aioredis.from_url() 是纯构造：不打开 TCP 连接，只建 ConnectionPool 对象
      → 真正的 TCP 连接在首次命令时 lazy 建立（redis-py 标准行为）
    - shutdown 阶段必须 await redis.aclose() 释放连接池 socket

Redis-py 5.x 推荐使用 aclose()（旧 close() 是兼容别名）。
"""
from __future__ import annotations

import logging

import redis.asyncio as aioredis

from shared.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)

# 连接池上限（远端 Redis 服务端 maxclients 通常 10000，但共享实例要克制）
MAX_CONNECTIONS = 20


def _build_client() -> aioredis.Redis:
    """按当前配置构建一个新的 Redis 客户端（含连接池）"""
    settings = get_settings()
    return aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        # 连接保活：避免远端 Redis 主动断开空闲连接导致 10054
        socket_keepalive=True,
        socket_timeout=5,
        socket_connect_timeout=5,
        # 健康检查：30s 一次 PING，失败自动重建
        health_check_interval=30,
        # 重试：超时/连接错误自动重试 1 次
        retry_on_timeout=True,
        retry_on_error=[ConnectionError, TimeoutError],
        # 连接池上限：防止被滥用拖垮 Redis 服务端
        max_connections=MAX_CONNECTIONS,
    )


# ★ 全局单例：from_url 只建连接池对象，不建 TCP 连接
redis: aioredis.Redis = _build_client()


async def close_redis_client() -> None:
    """关闭连接池（lifespan shutdown 调用）

    释放所有 pooled socket；调用后 `redis` 不可再用。
    """
    await redis.aclose()


__all__ = [
    "MAX_CONNECTIONS",
    "_build_client",
    "close_redis_client",
    "redis",
]
