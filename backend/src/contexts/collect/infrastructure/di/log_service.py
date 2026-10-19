"""log_service — CollectLogService DI 工厂

Phase 2 重构（2026-10-19）：日志子系统独立闭环
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.infrastructure.di.db_session import get_db
from shared.infrastructure.di.redis_session import get_redis
from contexts.collect.application.service.manage import CollectLogService


async def get_collect_log_service(
    session: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> CollectLogService:
    """注入 CollectLogService 依赖

    使用场景：
        1. log_handler.py 注入：用于查询
        2. 采集接口 service 注入：用于 create_pending / mark_failed
    """
    return CollectLogService(session=session, redis_client=redis)


__all__ = ["get_collect_log_service"]
