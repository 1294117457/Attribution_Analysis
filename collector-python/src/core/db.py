"""数据库：ORM 基类 + 时间戳混入 + engine/session 工厂（三合一，原分 3 个文件）。

两个物理库：db_*（业务库 attribution_db）、raw_*（采集库 raw_data_db）。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import NullPool

from core.config import get_settings


class AttribBase(DeclarativeBase):
    """业务库 ORM 基类（attribution_db）"""


class RawBase(DeclarativeBase):
    """采集库 ORM 基类（raw_data_db）"""


# 向后兼容旧 import（过渡期）
Base = AttribBase


class TimestampMixin:
    """自动管理 created_at / updated_at

    ⚠️ 必须用 timezone=True —— 与库表 DDL 的 timestamptz 对齐。
    asyncpg 写 aware datetime 到 naive 列会直接报错；反之 naive 写进 timestamptz
    会按会话时区解释，跨时区部署后语义漂移。
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


settings = get_settings()

db_async_engine = create_async_engine(
    settings.DATABASE_URL, echo=settings.DEBUG,
    poolclass=NullPool,  # 避免事件循环绑定问题（兼容 pytest + uvicorn 多场景）
    pool_pre_ping=True,
)
db_session_factory = async_sessionmaker(
    bind=db_async_engine, class_=AsyncSession,
    expire_on_commit=False, autocommit=False, autoflush=False)

_raw_url = settings.RAW_DATABASE_URL or settings.DATABASE_URL
raw_async_engine = create_async_engine(
    _raw_url, echo=settings.DEBUG, poolclass=NullPool, pool_pre_ping=True)
raw_session_factory = async_sessionmaker(
    bind=raw_async_engine, class_=AsyncSession,
    expire_on_commit=False, autocommit=False, autoflush=False)


async def close_db() -> None:
    """关闭连接池（NullPool 不需要 dispose，但保持接口兼容）"""
    await db_async_engine.dispose()
    await raw_async_engine.dispose()


__all__ = ["AttribBase", "RawBase", "Base", "TimestampMixin",
           "db_async_engine", "raw_async_engine",
           "db_session_factory", "raw_session_factory", "close_db"]
