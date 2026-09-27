"""依赖注入（DI）工厂

为 FastAPI route 层提供 application service 的 Depends 工厂。
DDD 改造核心：把 Repo/Service 构造从 application 层挪到 infrastructure，
application 层只接收已构造好的依赖（依赖反转）。

用法（route 层）：
    from infrastructure.config.di import get_kline_app_service

    @router.post("/kline/collect")
    async def collect(
        req: KlineCollectRequest,
        service: KlineAppService = Depends(get_kline_app_service),
    ):
        ...
"""
from __future__ import annotations

from typing import Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from application.port.registry import get_registry
from application.port.collector_port import KlineFetcher
from application.service.kline_app_service import KlineAppService
from application.service.panel_app_service import StockPanelAppService
from domain.concept.service import ConceptBriefService
from domain.kline.service import IndicatorCalculator
from infrastructure.persistence.connection import get_db
from infrastructure.persistence.repositories.concept_repository import ConceptRepoImpl
from infrastructure.persistence.repositories.kline_repository import KlineRepoImpl
from infrastructure.persistence.repositories.panel_compose_repository import (
    StockPanelComposeRepoImpl,
)
from infrastructure.persistence.repositories.stock_repository import StockRepoImpl


# ── Kline ────────────────────────────────────────────────────────────────────

def get_indicator_calculator() -> IndicatorCalculator:
    """IndicatorCalculator 单例（无状态，可复用）"""
    return IndicatorCalculator()


def get_kline_app_service(
    session: AsyncSession = Depends(get_db),
    indicator_calc: IndicatorCalculator = Depends(get_indicator_calculator),
) -> KlineAppService:
    """K线应用服务 — 注入 Repository（领域接口）"""
    kline_repo = KlineRepoImpl(session)
    stock_repo = StockRepoImpl(session)
    return KlineAppService(
        kline_repo=kline_repo,
        stock_repo=stock_repo,
        indicator_calc=indicator_calc,
    )


def get_kline_fetcher() -> KlineFetcher:
    """K线 fetcher（从注册中心取）"""
    return get_registry().get(KlineFetcher)


# ── Panel ────────────────────────────────────────────────────────────────────

def get_concept_brief_service() -> ConceptBriefService:
    """概念摘要领域服务（无 IO，可单例）"""
    return ConceptBriefService()


def get_panel_app_service(
    session: AsyncSession = Depends(get_db),
    brief_service: ConceptBriefService = Depends(get_concept_brief_service),
) -> StockPanelAppService:
    """Panel 应用服务 — 注入 concept repo + brief service"""
    concept_repo = ConceptRepoImpl(session)
    return StockPanelAppService(
        session=session,
        concept_repo=concept_repo,
        brief_service=brief_service,
    )
