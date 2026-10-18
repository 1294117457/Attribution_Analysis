"""market context — 业务 DI 工厂

仅负责：组装 market 相关的 service（StockInfoService / ConceptService / ConceptBoardService）。

**不包含** 纯资源 DI（get_db / get_redis 等）—— 那些在 `shared.infrastructure.di`。
**不包含** ConceptService / ConceptBoardService 工厂 —— ConceptService 工厂在本 context
单独 `concept.py`，因为它涉及跨 context（依赖 collect 的 ServiceRegistry）。
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.infrastructure.di.db_session import get_db, get_raw_db


def get_stock_info_service(
    attr_session: AsyncSession = Depends(get_db),
    raw_session: AsyncSession = Depends(get_raw_db),
):
    """StockInfoService 工厂（双 session：业务库 + 采集库）"""
    from contexts.concept.domain.services.concept_brief_service import ConceptBriefService
    from contexts.concept.infrastructure.persistence.repositories.concept_repository import (
        ConceptRepoImpl,
    )
    from contexts.market.application.service.stock_info_service import StockInfoService
    from contexts.market.domain.services.indicator_calculator import IndicatorCalculator
    from contexts.market.infrastructure.persistence.repositories.kline_repository import (
        KlineRepoImpl,
    )
    from contexts.market.infrastructure.persistence.repositories.panel_compose_repository import (
        StockPanelComposeRepoImpl,
    )
    from contexts.market.infrastructure.persistence.repositories.stock_repository import (
        StockRepoImpl,
    )
    from contexts.user.infrastructure.persistence.repositories.pool_repository import (
        StockPoolRepoImpl,
    )

    # step7: 同步股票列表改调 StockBasicService（fetcher 内部 lazy init tushare 单例）
    from contexts.collect.application.service.fundamental.stock_basic_service import (
        StockBasicService,
    )
    stock_basic_svc = StockBasicService()

    return StockInfoService(
        stock_repo=StockRepoImpl(raw_session, attr_session),
        kline_repo=KlineRepoImpl(raw_session),
        pool_repo=StockPoolRepoImpl(attr_session),
        panel_repo=StockPanelComposeRepoImpl(raw_session, attr_session),
        concept_repo=ConceptRepoImpl(raw_session, attr_session),
        brief_service=ConceptBriefService(),
        indicator_calc=IndicatorCalculator(),
        stock_basic_svc=stock_basic_svc,
    )


__all__ = ["get_stock_info_service"]
