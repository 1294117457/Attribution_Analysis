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

    ★ 各 service 的构造签名不同（v4 自管协议）：
        DailyService        (log_service, session=None, fetcher=None)
        DailyBasicService   (session, log_service, task_runner, ...)
        AdjFactorService    (session, log_service, task_runner, ...)
      这里按 task_type 分别组装 —— 统一走 CollectLogService + TaskRunner，
      session 传 None（后台任务自己开 raw_data session）。
    """
    from contexts.collect.application.service.manage import CollectLogService
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
    if task_type == "daily":
        return DailyService(log_service=CollectLogService())
    if task_type == "daily_basic":
        from contexts.collect.infrastructure.adapter.background import (
            get_collect_task_runner,
        )
        return DailyBasicService(
            session=None,
            log_service=CollectLogService(),
            task_runner=get_collect_task_runner(),
        )
    if task_type == "adj_factor":
        from contexts.collect.infrastructure.adapter.background import (
            get_collect_task_runner,
        )
        return AdjFactorService(
            session=None,
            log_service=CollectLogService(),
            task_runner=get_collect_task_runner(),
        )
    raise ValueError(f"pool 不支持的 task_type: {task_type}")


async def _run_collect_one(task_type: str, symbol: str, params: dict):
    """stock_pool 触发采集的简单 wrapper（白名单 + DefaultConstruct）

    ★ daily v6（按时间采集）：symbol 必须透传成 ts_code，
      否则会退化成「全市场采集」——每个池成员都触发一次全市场拉取。
    """
    svc = _build_collect_service(task_type)
    if task_type == "daily" and symbol:
        params = {**params, "symbol": symbol}
    await svc.collect(params)


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
