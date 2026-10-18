"""shared.infrastructure.connection

资源连接层（不含 FastAPI Depends）—— 仅负责"怎么造资源"：
- db_factory:    async engine + async sessionmaker 实例
- redis_client:  aioredis 客户端构造

依赖注入（get_db / get_raw_db / get_redis）在 `shared.infrastructure.di`。
"""
from shared.infrastructure.connection.db_factory import (
    close_db,
    db_async_engine,
    db_session_factory,
    raw_async_engine,
    raw_session_factory,
)
from shared.infrastructure.connection.redis_client import MAX_CONNECTIONS, _build_client

__all__ = [
    # db_factory
    "db_async_engine",
    "raw_async_engine",
    "db_session_factory",
    "raw_session_factory",
    "close_db",
    # redis_client
    "MAX_CONNECTIONS",
    "_build_client",
]
