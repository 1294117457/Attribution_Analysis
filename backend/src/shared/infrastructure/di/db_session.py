"""DB session 依赖注入工厂

仅负责：给 route 层 / scheduler 层 / 后台任务 提供 session 实例。

包含：
- get_db / get_raw_db:                FastAPI Depends 用
- get_db_context / get_raw_db_context: Service 层独立事务用（async with）

**不创建** engine / sessionmaker —— 那些在 `shared.infrastructure.connection.db_factory`。
**不包含** 业务 service 工厂 —— 那些在各 `contexts/<ctx>/infrastructure/di/`。

使用示例（route 层）：
    @router.get(...)
    async def list_users(db: AsyncSession = Depends(get_db)):
        ...

使用示例（service 层后台任务）：
    async with get_db_context() as session:
        ...
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from shared.infrastructure.connection.db_factory import (
    db_session_factory,
    raw_session_factory,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Depends 注入用（业务库 attribution_db）"""
    async with db_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_raw_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Depends 注入用（采集库 raw_data_db）

    与 get_db 互不干扰：两个 Depends 各自一个 session 各自一个事务。
    需要"业务表 + 采集表"的应用层方法接收两个 session 后在内存合并。
    """
    async with raw_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Service 层独立事务用（业务库）"""
    async with db_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_raw_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Service 层独立事务用（采集库）"""
    async with raw_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


__all__ = [
    "get_db",
    "get_raw_db",
    "get_db_context",
    "get_raw_db_context",
]
