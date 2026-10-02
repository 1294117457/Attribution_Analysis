"""依赖注入（DI）工厂

为 FastAPI route 层提供 application service 的 Depends 工厂。
DDD 改造核心：把 Repo/Service 构造从 application 层挪到 infrastructure，
application 层只接收已构造好的依赖（依赖反转）。

约定：
- 所有 AppService 工厂都集中在此；route 层只 Depends(...)
- CollectAppService 例外：独立构造，不走 Depends（lifespan + APScheduler 用）
- 概念与池服务的 ConceptFetcher 由 setup_default_registry() 在 lifespan 注册

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

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from application.port.collector_port import ConceptFetcher, KlineFetcher
from application.port.registry import get_registry
from application.service.concept_app_service import ConceptAppService
from application.service.kline_app_service import KlineAppService
from application.service.panel_app_service import StockPanelAppService
from application.service.pool_app_service import StockPoolAppService
from application.service.pool_operation_app_service import PoolOperationAppService
from application.service.stock_analysis_app_service import StockAnalysisAppService
from application.service.stock_app_service import StockAppService
from application.service.auth_app_service import AuthAppService
from domain.service import ConceptBriefService, IndicatorCalculator
from infrastructure.persistence.connection import get_db
from infrastructure.persistence.repositories.concept_repository import ConceptRepoImpl
from infrastructure.persistence.repositories.kline_repository import KlineRepoImpl
from infrastructure.persistence.repositories.panel_compose_repository import (
    StockPanelComposeRepoImpl,
)
from infrastructure.persistence.repositories.pool_operation_repository import (
    PoolOperationRepoImpl,
)
from infrastructure.persistence.repositories.pool_repository import StockPoolRepoImpl
from infrastructure.persistence.repositories.stock_repository import StockRepoImpl


# ── 通用领域服务（无 IO，可单例） ─────────────────────────────────────────────


def get_indicator_calculator() -> IndicatorCalculator:
    """IndicatorCalculator 单例（无状态，可复用）"""
    return IndicatorCalculator()


def get_concept_brief_service() -> ConceptBriefService:
    """概念摘要领域服务（无 IO，可单例）"""
    return ConceptBriefService()


# ── Fetcher（注册中心取） ────────────────────────────────────────────────────


def get_kline_fetcher() -> KlineFetcher:
    """K线 fetcher（从注册中心取）"""
    return get_registry().get(KlineFetcher)


# ── Kline ────────────────────────────────────────────────────────────────────


def get_kline_app_service(
    session: AsyncSession = Depends(get_db),
    indicator_calc: IndicatorCalculator = Depends(get_indicator_calculator),
) -> KlineAppService:
    """K线应用服务 — 注入 Repository（领域接口）"""
    return KlineAppService(
        kline_repo=KlineRepoImpl(session),
        stock_repo=StockRepoImpl(session),
        indicator_calc=indicator_calc,
    )


# ── Stock ────────────────────────────────────────────────────────────────────


def get_stock_app_service(
    session: AsyncSession = Depends(get_db),
) -> StockAppService:
    """股票应用服务（CRUD + 元数据）"""
    return StockAppService(session=session)


# ── Concept ────────────────────────────────────────────────────────────────────


def get_concept_app_service(
    session: AsyncSession = Depends(get_db),
) -> ConceptAppService:
    """概念应用服务（查询 + 实时反查）"""
    registry = get_registry()
    if not registry.has(ConceptFetcher):
        raise HTTPException(503, "概念采集器未注册")
    return ConceptAppService(
        repo=ConceptRepoImpl(session),
        fetcher=registry.get(ConceptFetcher),
    )


# ── Panel ────────────────────────────────────────────────────────────────────


def get_panel_app_service(
    session: AsyncSession = Depends(get_db),
    brief_service: ConceptBriefService = Depends(get_concept_brief_service),
) -> StockPanelAppService:
    """Panel 应用服务 — 注入 concept repo + brief service"""
    return StockPanelAppService(
        session=session,
        concept_repo=ConceptRepoImpl(session),
        brief_service=brief_service,
    )


# ── Pool ─────────────────────────────────────────────────────────────────────


def get_pool_app_service(
    session: AsyncSession = Depends(get_db),
) -> StockPoolAppService:
    """操作池应用服务（CRUD + 成员管理）"""
    return StockPoolAppService(session=session)


def get_pool_operation_app_service(
    session: AsyncSession = Depends(get_db),
) -> PoolOperationAppService:
    """池操作应用服务（后台派发 + 进度查询）"""
    return PoolOperationAppService(session=session)


# ── Stock Analysis ──────────────────────────────────────────────────────────


def get_stock_analysis_app_service(
    session: AsyncSession = Depends(get_db),
) -> StockAnalysisAppService:
    """股票归因分析服务（聚合视图，AI 入口）"""
    return StockAnalysisAppService(
        stock_repo=StockRepoImpl(session),
        kline_repo=KlineRepoImpl(session),
        pool_repo=StockPoolRepoImpl(session),
    )


# ── Auth ──────────────────────────────────────────────────────────────────


def get_auth_app_service(
    session: AsyncSession = Depends(get_db),
) -> AuthAppService:
    """认证授权应用服务"""
    return AuthAppService(session=session)