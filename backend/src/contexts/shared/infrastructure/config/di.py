"""依赖注入（DI）工厂 — 阶段 B/C/D 后的新位置

把 application service / repo / adapter 工厂集中在这里。
- route 层只 Depends(...) 这些工厂
- 各 context 内的 bootstrap 不会重复定义工厂
- 保留 03-依赖矩阵与启动序列.md §3.3 的启动顺序约束
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# ── 通用领域服务（无 IO，可单例）──
from contexts.market.domain.service.indicator_calculator import IndicatorCalculator
from contexts.concept.domain.service.concept_brief_service import ConceptBriefService
from contexts.collect.domain.service.concept_collection_policy import ConceptCollectionPolicy

# ── Auth 端口实现（依然放 infra/）──
from contexts.auth.infrastructure.adapter.auth_port_adapters import (
    BcryptPasswordHasher,
    CaptchaAdapter,
    EmailVerificationAdapter,
    JwtAdapter,
)

# ── DB session / ORM registry ──
from contexts.shared.infrastructure.persistence.connection import (
    AsyncSessionLocal,
    get_db,
)
from contexts.shared.infrastructure.persistence import models_registry  # noqa: F401 触发 ORM 注册

if TYPE_CHECKING:
    from contexts.collect.application.collect import CollectContext, CollectRunner
    from contexts.collect.application.port.collect_port import (
        CollectProgressPort,
        CollectTaskStorePort,
    )
    from contexts.data.application.port.base import DataGatewayPort
    from contexts.collect.application.port.scheduler_port import SchedulerPort
    from contexts.concept.application.service.concept_realtime import ConceptRealtimeReader
    from contexts.data.application.service.data_query_service import DataQueryService
    from contexts.auth.application.service.auth_service import AuthService
    from contexts.collect.application.service.collect_manage_service import CollectManageService
    from contexts.concept.application.service.concept_board_service import ConceptBoardService
    from contexts.concept.application.service.concept_service import ConceptService
    from contexts.market.application.service.stock_info_service import StockInfoService
    from contexts.user.application.service.stock_pool_service import StockPoolService

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  通用领域服务工厂
# ═══════════════════════════════════════════════════════════════════════════════

def get_indicator_calculator() -> IndicatorCalculator:
    return IndicatorCalculator()


def get_concept_brief_service() -> ConceptBriefService:
    return ConceptBriefService()


def get_concept_collection_policy() -> ConceptCollectionPolicy:
    return ConceptCollectionPolicy()


# ═══════════════════════════════════════════════════════════════════════════════
#  Data 统一入口
# ═══════════════════════════════════════════════════════════════════════════════

def get_data_gateway() -> "DataGatewayPort":
    from contexts.data.infrastructure.adapter import get_data_gateway as _ggw
    return _ggw()


def get_data_query_service() -> "DataQueryService":
    from contexts.data.application.service.data_query_service import DataQueryService
    return DataQueryService(get_data_gateway())


def _concept_realtime_reader(repo) -> "ConceptRealtimeReader":
    from contexts.concept.application.service.concept_realtime import ConceptRealtimeReader
    return ConceptRealtimeReader(get_data_gateway(), repo)


# ═══════════════════════════════════════════════════════════════════════════════
#  Auth 端口工厂
# ═══════════════════════════════════════════════════════════════════════════════

def get_password_hasher() -> BcryptPasswordHasher:
    return BcryptPasswordHasher()


def get_jwt_service() -> JwtAdapter:
    return JwtAdapter()


def get_captcha() -> CaptchaAdapter:
    return CaptchaAdapter()


def get_email_verification_store() -> EmailVerificationAdapter:
    return EmailVerificationAdapter()


# ═══════════════════════════════════════════════════════════════════════════════
#  Collect 子系统
# ═══════════════════════════════════════════════════════════════════════════════

def get_collect_progress() -> "CollectProgressPort":
    from contexts.collect.infrastructure.adapter.cache.collect_progress import RedisCollectProgress
    return RedisCollectProgress()


def get_collect_task_store() -> "CollectTaskStorePort":
    from contexts.collect.infrastructure.persistence.collect.task_store import SqlCollectTaskStore
    return SqlCollectTaskStore()


def get_collect_runner() -> "CollectRunner":
    from contexts.collect.application.collect import CollectRunner
    return CollectRunner(tasks=get_collect_task_store(), progress=get_collect_progress())


@asynccontextmanager
async def _session_ctx() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


@asynccontextmanager
async def _stock_info_scope() -> AsyncIterator["StockInfoService"]:
    from contexts.market.infrastructure.persistence.repositories.stock_repository import StockRepoImpl
    from contexts.market.infrastructure.persistence.repositories.kline_repository import KlineRepoImpl
    from contexts.user.infrastructure.persistence.repositories.pool_repository import StockPoolRepoImpl
    from contexts.market.infrastructure.persistence.repositories.panel_compose_repository import (
        StockPanelComposeRepoImpl,
    )
    from contexts.concept.infrastructure.persistence.repositories.concept_repository import ConceptRepoImpl
    from contexts.market.application.service.stock_info_service import StockInfoService
    async with AsyncSessionLocal() as session:
        yield StockInfoService(
            stock_repo=StockRepoImpl(session),
            kline_repo=KlineRepoImpl(session),
            pool_repo=StockPoolRepoImpl(session),
            panel_repo=StockPanelComposeRepoImpl(session),
            concept_repo=ConceptRepoImpl(session),
            brief_service=ConceptBriefService(),
            indicator_calc=IndicatorCalculator(),
            gateway=get_data_gateway(),
        )
        await session.commit()


def build_collect_context() -> "CollectContext":
    from contexts.collect.application.collect import CollectContext
    from contexts.collect.infrastructure.persistence.collect.concept_store import SqlConceptStore
    from contexts.collect.infrastructure.persistence.collect.raw_store import SqlRawDataStore
    from contexts.collect.infrastructure.persistence.collect.stock_universe import SqlStockUniverse
    from contexts.shared.infrastructure.config.settings import get_settings

    s = get_settings()
    return CollectContext(
        gateway=get_data_gateway(),
        raw_store=SqlRawDataStore(),
        stocks=SqlStockUniverse(),
        concepts=SqlConceptStore(),
        tasks=get_collect_task_store(),
        progress=get_collect_progress(),
        stock_info=_stock_info_scope,
        concurrency=s.COLLECT_CONCURRENCY,
        max_concurrency=s.COLLECT_MAX_CONCURRENCY,
    )


_scheduler: "SchedulerPort | None" = None


def set_scheduler(scheduler: "SchedulerPort | None") -> None:
    global _scheduler
    _scheduler = scheduler


def get_collect_manage_service() -> "CollectManageService":
    from contexts.collect.application.service.collect_manage_service import CollectManageService
    from contexts.collect.application.collect import get_collect_task_registry
    from contexts.collect.infrastructure.persistence.repositories.collect_config_repository import (
        CollectConfigRepoImpl,
    )
    return CollectManageService(
        progress=get_collect_progress(),
        tasks=get_collect_task_store(),
        runner=get_collect_runner(),
        task_registry=get_collect_task_registry(),
        scheduler=_scheduler,
        config_repo=CollectConfigRepoImpl(),
        gateway=get_data_gateway(),
        session_factory=_session_ctx,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Route 层 Depends 工厂
# ═══════════════════════════════════════════════════════════════════════════════

def get_auth_service(
    session: AsyncSession = Depends(get_db),
    hasher: BcryptPasswordHasher = Depends(get_password_hasher),
    jwt: JwtAdapter = Depends(get_jwt_service),
    captcha: CaptchaAdapter = Depends(get_captcha),
    email_store: EmailVerificationAdapter = Depends(get_email_verification_store),
) -> "AuthService":
    from contexts.auth.application.service.auth_service import AuthService
    from contexts.auth.infrastructure.persistence.repositories.auth_repository import (
        PermissionRepoImpl, RefreshTokenRepoImpl, RoleRepoImpl, UserRepoImpl,
    )
    return AuthService(
        users=UserRepoImpl(session),
        roles=RoleRepoImpl(session),
        perms=PermissionRepoImpl(session),
        refresh=RefreshTokenRepoImpl(),
        hasher=hasher,
        captcha=captcha,
        email_verify=email_store,
        jwt=jwt,
    )


def get_stock_info_service(
    session: AsyncSession = Depends(get_db),
    indicator_calc: IndicatorCalculator = Depends(get_indicator_calculator),
    brief_service: ConceptBriefService = Depends(get_concept_brief_service),
) -> "StockInfoService":
    from contexts.market.infrastructure.persistence.repositories.stock_repository import StockRepoImpl
    from contexts.market.infrastructure.persistence.repositories.kline_repository import KlineRepoImpl
    from contexts.user.infrastructure.persistence.repositories.pool_repository import StockPoolRepoImpl
    from contexts.market.infrastructure.persistence.repositories.panel_compose_repository import (
        StockPanelComposeRepoImpl,
    )
    from contexts.concept.infrastructure.persistence.repositories.concept_repository import ConceptRepoImpl
    from contexts.market.application.service.stock_info_service import StockInfoService
    return StockInfoService(
        stock_repo=StockRepoImpl(session),
        kline_repo=KlineRepoImpl(session),
        pool_repo=StockPoolRepoImpl(session),
        panel_repo=StockPanelComposeRepoImpl(session),
        concept_repo=ConceptRepoImpl(session),
        brief_service=brief_service,
        indicator_calc=indicator_calc,
        gateway=get_data_gateway(),
    )


def get_concept_service(
    session: AsyncSession = Depends(get_db),
) -> "ConceptService":
    from contexts.concept.application.service.concept_service import ConceptService
    from contexts.concept.infrastructure.persistence.repositories.concept_repository import ConceptRepoImpl
    repo = ConceptRepoImpl(session)
    return ConceptService(
        repo=repo,
        gateway=get_data_gateway(),
        realtime=_concept_realtime_reader(repo),
    )


def get_concept_board_service(
    session: AsyncSession = Depends(get_db),
) -> "ConceptBoardService":
    from contexts.concept.application.service.concept_board_service import ConceptBoardService
    from contexts.concept.infrastructure.persistence.repositories.concept_repository import ConceptRepoImpl
    repo = ConceptRepoImpl(session)
    return ConceptBoardService(repo=repo, realtime=_concept_realtime_reader(repo))


def get_stock_pool_service(
    session: AsyncSession = Depends(get_db),
) -> "StockPoolService":
    from contexts.user.application.service.stock_pool_service import StockPoolService
    from contexts.market.infrastructure.persistence.repositories.stock_repository import StockRepoImpl
    from contexts.user.infrastructure.persistence.repositories.pool_repository import StockPoolRepoImpl
    from contexts.user.infrastructure.persistence.repositories.pool_operation_repository import (
        PoolOperationRepoImpl,
    )
    from contexts.user.infrastructure.adapter.background.operation_dispatcher import OperationDispatcher
    return StockPoolService(
        pool_repo=StockPoolRepoImpl(session),
        stock_repo=StockRepoImpl(session),
        op_repo=PoolOperationRepoImpl(session),
        dispatcher=OperationDispatcher(
            run_one=lambda t, u, p: get_collect_manage_service().run_one(t, u, p),
        ),
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Scheduler 工厂（带 session 参数的同步构造版）
# ═══════════════════════════════════════════════════════════════════════════════

def build_stock_info_service(session: AsyncSession) -> "StockInfoService":
    from contexts.market.infrastructure.persistence.repositories.stock_repository import StockRepoImpl
    from contexts.market.infrastructure.persistence.repositories.kline_repository import KlineRepoImpl
    from contexts.user.infrastructure.persistence.repositories.pool_repository import StockPoolRepoImpl
    from contexts.market.infrastructure.persistence.repositories.panel_compose_repository import (
        StockPanelComposeRepoImpl,
    )
    from contexts.concept.infrastructure.persistence.repositories.concept_repository import ConceptRepoImpl
    from contexts.market.application.service.stock_info_service import StockInfoService
    return StockInfoService(
        stock_repo=StockRepoImpl(session),
        kline_repo=KlineRepoImpl(session),
        pool_repo=StockPoolRepoImpl(session),
        panel_repo=StockPanelComposeRepoImpl(session),
        concept_repo=ConceptRepoImpl(session),
        brief_service=ConceptBriefService(),
        indicator_calc=IndicatorCalculator(),
        gateway=get_data_gateway(),
    )


def build_concept_service(session: AsyncSession) -> "ConceptService":
    from contexts.concept.application.service.concept_service import ConceptService
    from contexts.concept.infrastructure.persistence.repositories.concept_repository import ConceptRepoImpl
    return ConceptService(repo=ConceptRepoImpl(session), gateway=get_data_gateway())


# ═══════════════════════════════════════════════════════════════════════════════
#  数据源初始化
# ═══════════════════════════════════════════════════════════════════════════════

def setup_default_registry() -> None:
    """注册全部数据源 Adapter 到 DataPortRegistry（lifespan 启动时调用，幂等）"""
    from contexts.data.infrastructure.adapter import setup_data
    setup_data()
