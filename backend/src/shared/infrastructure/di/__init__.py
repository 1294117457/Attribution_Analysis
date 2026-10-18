"""shared.infrastructure.di

基础设施级依赖注入工厂（仅资源依赖，无业务）。

包含：
- db_session:   get_db / get_raw_db / get_db_context / get_raw_db_context
- redis_session: get_redis / close_redis

**不包含** 业务 service 工厂 —— 那些在各 `contexts/<ctx>/infrastructure/di/`。
"""
from shared.infrastructure.di.db_session import (
    get_db,
    get_db_context,
    get_raw_db,
    get_raw_db_context,
)
from shared.infrastructure.di.redis_session import close_redis, get_redis

__all__ = [
    # db_session
    "get_db",
    "get_raw_db",
    "get_db_context",
    "get_raw_db_context",
    # redis_session
    "get_redis",
    "close_redis",
]
