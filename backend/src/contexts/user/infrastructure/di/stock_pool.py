"""user context — 业务 DI 工厂

仅负责：组装 StockPoolService（用户的自选股池服务）。

依赖 collect 的 service（pool 触发采集）—— 跨 context 通过 dict 映射的 service factory 完成。
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.infrastructure.di.db_session import get_db


# pool 触发采集支持的服务白名单（task_type → service 工厂）
# 注：service 内部直接 import fetcher 构造，不依赖 ServiceRegistry
def _build_collect_service(task_type: str):
    """根据 task_type 构造对应的 collect service

    注：service 自身 __init__ 已不依赖 fetcher 注入
    （fetcher 内部 lazy init tushare/adata 单例），
    所以这里直接 DefaultConstruct。
    """
    from contexts.collect.application.service.fundamental.daily_basic_service import (
        DailyBasicService,
    )
    from contexts.collect.application.service.tech.daily_service import (
        DailyService,
    )
    from contexts.collect.application.service.tech.adj_factor_service import (
        AdjFactorService,
    )

    # task_type 键保持稳定：URL/service_name，不能改
    factory = {
        "daily_kline": DailyService,
        "daily_basic": DailyBasicService,
        "adj_factor": AdjFactorService,
    }.get(task_type)
    if factory is None:
        raise ValueError(f"pool 不支持的 task_type: {task_type}")
    return factory()


async def _run_collect_one(task_type: str, user_id: int, params: dict):
    """stock_pool 触发采集的简单 wrapper（白名单 + DefaultConstruct）"""
    svc = _build_collect_service(task_type)
    return await svc.collect(params)


def get_stock_pool_service(
    session: AsyncSession = Depends(get_db),
):
    """StockPoolService 工厂"""
    from contexts.market.infrastructure.persistence.repositories.stock_repository import (
        StockRepoImpl,
    )
    from contexts.user.application.service.stock_pool_service import StockPoolService
    from contexts.user.infrastructure.adapter.background.operation_dispatcher import (
        OperationDispatcher,
    )
    from contexts.user.infrastructure.persistence.repositories.pool_operation_repository import (
        PoolOperationRepoImpl,
    )
    from contexts.user.infrastructure.persistence.repositories.pool_repository import (
        StockPoolRepoImpl,
    )

    return StockPoolService(
        pool_repo=StockPoolRepoImpl(session),
        stock_repo=StockRepoImpl(session),
        op_repo=PoolOperationRepoImpl(session),
        dispatcher=OperationDispatcher(
            run_one=_run_collect_one,
        ),
    )


__all__ = ["get_stock_pool_service"]
