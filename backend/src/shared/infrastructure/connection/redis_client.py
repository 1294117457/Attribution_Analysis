"""Redis 异步客户端构造

仅负责：按当前 settings 构造一个 aioredis.Redis 客户端（含连接池）。

**不包含** 单例管理 —— 那是 `get_redis()` 的职责，在 `shared.infrastructure.di.redis_session`。
**不包含** FastAPI Depends 工厂 —— 也在 `di/redis_session.py`。

设计理由：
- `_build_client()` 是纯函数：输入 settings → 输出 aioredis.Redis
- 便于单测：直接调 `_build_client(stub_settings)` 拿到独立客户端
- 单例管理（事件循环内 lazy init + Lock）放 di 层

使用示例：
    from shared.infrastructure.connection.redis_client import _build_client
    client = _build_client()
"""
from __future__ import annotations

import redis.asyncio as aioredis

from shared.infrastructure.config.settings import get_settings

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


__all__ = ["_build_client", "MAX_CONNECTIONS"]
