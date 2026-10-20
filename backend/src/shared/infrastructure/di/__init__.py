"""shared.infrastructure.di

基础设施级 session 依赖注入工厂（仅资源依赖，无业务）。

包含：
- db_session:   get_db / get_raw_db / get_db_context / get_raw_db_context

**Redis 已改为全局单例** —— 直接
    from shared.infrastructure.connection.redis_client import redis as redis_client
无需任何 DI / Depends 注入。

**不包含** 业务 service 工厂 —— 那些在各 `contexts/<ctx>/infrastructure/di/`。
"""
from shared.infrastructure.di.db_session import (
    get_db,
    get_db_context,
    get_raw_db,
    get_raw_db_context,
)
from shared.infrastructure.connection.db_factory import (
    db_session_factory,
    raw_session_factory,
)

__all__ = [
    # db_session
    "get_db",
    "get_raw_db",
    "get_db_context",
    "get_raw_db_context",
    # db_factory
    "db_session_factory",
    "raw_session_factory",
]
