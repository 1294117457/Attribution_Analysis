"""数据库连接工厂

仅负责：
- 构造 async engine（attribution_db 业务库 + raw_data_db 采集库）
- 构造 async sessionmaker 实例（db_session_factory / raw_session_factory）
- 关闭连接池（close_db）

**不包含** FastAPI Depends 工厂 —— 那些在 `shared.infrastructure.di.db_session`。
**不包含** 配置（settings）—— 配置在 `shared.infrastructure.config.settings`。

使用示例：
    from shared.infrastructure.connection.db_factory import db_session_factory
    async with db_session_factory() as session:
        ...
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from shared.infrastructure.config.settings import get_settings

settings = get_settings()

# 业务库（attribution_db）
db_async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    poolclass=NullPool,  # 避免事件循环绑定问题（兼容 pytest + uvicorn 多场景）
    pool_pre_ping=True,
)

# 业务库 session 工厂
db_session_factory = async_sessionmaker(
    bind=db_async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 采集库（raw_data_db）—— 允许与业务库同 URL（dev 模式）
_raw_url = settings.RAW_DATABASE_URL or settings.DATABASE_URL
raw_async_engine = create_async_engine(
    _raw_url,
    echo=settings.DEBUG,
    poolclass=NullPool,
    pool_pre_ping=True,
)

# 采集库 session 工厂
raw_session_factory = async_sessionmaker(
    bind=raw_async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def close_db() -> None:
    """关闭连接池（NullPool 不需要 dispose，但保持接口兼容）"""
    await db_async_engine.dispose()
    await raw_async_engine.dispose()


__all__ = [
    "db_async_engine",
    "raw_async_engine",
    "db_session_factory",
    "raw_session_factory",
    "close_db",
]
