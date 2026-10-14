"""依赖注入（DI）工厂

为 FastAPI route 层提供 application service 的 Depends 工厂。
DDD 改造核心：把 Repo/Service 构造从 application 层挪到 infrastructure，
application 层只接收已构造好的依赖（依赖反转）。

约定：
- 所有 service 工厂都集中在此；route 层只 Depends(...)
- scheduler / 后台任务走 `build_*_service(session)` 显式工厂（带 session 注入仓储）
- 数据源 Adapter 在 `setup_default_registry()` 内注册（lifespan 时调用）

用法（route 层）：
    from infrastructure.config.di import get_stock_info_service

    @router.post("/kline/collect")
    async def collect(
        req: KlineCollectRequest,
        service: StockInfoService = Depends(get_stock_info_service),
    ):
        ...
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncIterator, Callable

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from domain.service import (
    ConceptBriefService,
    ConceptCollectionPolicy,
    IndicatorCalculator,
)
from infrastructure.adapter.auth_port_adapters import (
    BcryptPasswordHasher,
    CaptchaAdapter,
    EmailVerificationAdapter,
    JwtAdapter,
)
if TYPE_CHECKING:
    # 仅供 type hint,避免循环 import
    from application.collect import CollectContext, CollectRunner
    from application.port.collect_port import (
        CollectProgressPort,
        CollectTaskStorePort,
    )
    from application.port.data import DataGatewayPort
    from application.port.scheduler_port import SchedulerPort
    from application.service.concept_realtime import ConceptRealtimeReader
    from application.service.data_query_service import DataQueryService
    from application.service import (
        AuthService,
        CollectManageService,
        ConceptBoardService,
        ConceptService,
        StockInfoService,
        StockPoolService,
    )
from infrastructure.persistence.connection import (
    AsyncSessionLocal,
    get_db,
)
from infrastructure.persistence.repositories.auth_repository import (
    PermissionRepoImpl,
    RefreshTokenRepoImpl,
    RoleRepoImpl,
    UserRepoImpl,
)
from infrastructure.persistence.repositories.collect_config_repository import (
    CollectConfigRepoImpl,
)
from infrastructure.persistence.repositories.concept_repository import (
    ConceptRepoImpl,
)
from infrastructure.persistence.repositories.kline_repository import (
    KlineRepoImpl,
)
from infrastructure.persistence.repositories.panel_compose_repository import (
    StockPanelComposeRepoImpl,
)
from infrastructure.persistence.repositories.pool_operation_repository import (
    PoolOperationRepoImpl,
)
from infrastructure.persistence.repositories.pool_repository import (
    StockPoolRepoImpl,
)
from infrastructure.persistence.repositories.stock_repository import StockRepoImpl

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  通用领域服务（无 IO，可单例）
# ═══════════════════════════════════════════════════════════════════════════════


def get_indicator_calculator() -> IndicatorCalculator:
    """IndicatorCalculator 单例（无状态，可复用）"""
    return IndicatorCalculator()


def get_concept_brief_service() -> ConceptBriefService:
    """概念摘要领域服务（无状态，可单例）"""
    return ConceptBriefService()


def get_concept_collection_policy() -> ConceptCollectionPolicy:
    """概念采集保护策略（无状态，可单例）"""
    return ConceptCollectionPolicy()


# ═══════════════════════════════════════════════════════════════════════════════
#  数据统一入口
# ═══════════════════════════════════════════════════════════════════════════════


def get_data_gateway() -> "DataGatewayPort":
    """数据统一入口（DataGateway 单例）"""
    from infrastructure.adapter.data import get_data_gateway as _ggw
    return _ggw()


def get_data_query_service() -> "DataQueryService":
    """按名调用入口（试查 / HTTP /data/* / Agent）"""
    from application.service.data_query_service import DataQueryService
    return DataQueryService(get_data_gateway())


def _concept_realtime_reader(repo: ConceptRepoImpl) -> "ConceptRealtimeReader":
    from application.service.concept_realtime import ConceptRealtimeReader
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
#  采集子系统端口适配（Sql 实现 + CollectRunner + CollectContext）
# ═══════════════════════════════════════════════════════════════════════════════


def get_collect_progress() -> "CollectProgressPort":
    """采集进度（Redis）"""
    from infrastructure.adapter.cache.collect_progress import RedisCollectProgress
    return RedisCollectProgress()


def get_collect_task_store() -> "CollectTaskStorePort":
    """采集任务行（sys_collect_tasks）"""
    from infrastructure.persistence.collect.task_store import SqlCollectTaskStore
    return SqlCollectTaskStore()


def get_collect_runner() -> "CollectRunner":
    """采集 runner（任务模板方法）"""
    from application.collect import CollectRunner
    return CollectRunner(tasks=get_collect_task_store(), progress=get_collect_progress())


@asynccontextmanager
async def _session_ctx() -> AsyncIterator[AsyncSession]:
    """Session 工厂"""
    async with AsyncSessionLocal() as session:
        yield session


@asynccontextmanager
async def _stock_info_scope() -> AsyncIterator["StockInfoService"]:
    """日 K / 股票清单复用 StockInfoService：每次调用开一个带 session 的 Service，退出时 commit"""
    from application.service import StockInfoService
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
    """采集用例子系统的依赖容器（lifespan 启动时调用一次）"""
    from application.collect import CollectContext
    from infrastructure.persistence.collect.concept_store import SqlConceptStore
    from infrastructure.persistence.collect.raw_store import SqlRawDataStore
    from infrastructure.persistence.collect.stock_universe import SqlStockUniverse
    from infrastructure.config.settings import get_settings

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
    """lifespan 启动调度器后注入；未启用时保持 None（方案仍可手动执行）"""
    global _scheduler
    _scheduler = scheduler


def get_collect_manage_service() -> "CollectManageService":
    """采集管理应用服务（依赖注入 · 同步）"""
    from application.service import CollectManageService
    from application.collect import get_collect_task_registry
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
    """认证授权应用服务"""
    from application.service import AuthService
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
    """股票信息应用服务（CRUD + K 线 + 归因 + 面板）"""
    from application.service import StockInfoService
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
    """概念基础查询服务（共享）"""
    from application.service import ConceptService
    repo = ConceptRepoImpl(session)
    return ConceptService(
        repo=repo,
        gateway=get_data_gateway(),
        realtime=_concept_realtime_reader(repo),
    )


def get_concept_board_service(
    session: AsyncSession = Depends(get_db),
) -> "ConceptBoardService":
    """概念大盘应用服务（大盘 + 概念 K 线）"""
    from application.service import ConceptBoardService
    repo = ConceptRepoImpl(session)
    return ConceptBoardService(repo=repo, realtime=_concept_realtime_reader(repo))


def get_stock_pool_service(
    session: AsyncSession = Depends(get_db),
) -> "StockPoolService":
    """操作池应用服务（CRUD + 成员 + 池操作派发）"""
    from application.service import StockPoolService
    from infrastructure.adapter.background.operation_dispatcher import (
        OperationDispatcher,
    )
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
    """为后台任务构造 StockInfoService（保留：外部 module 仍可能 import）"""
    from application.service import StockInfoService
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
    """为后台任务构造 ConceptService（采集任务 / 反查）"""
    from application.service import ConceptService
    return ConceptService(repo=ConceptRepoImpl(session), gateway=get_data_gateway())


# ═══════════════════════════════════════════════════════════════════════════════
#  数据源初始化
# ═══════════════════════════════════════════════════════════════════════════════


def setup_default_registry() -> None:
    """注册全部数据源 Adapter 到 DataPortRegistry（lifespan 启动时调用，幂等）"""
    from infrastructure.adapter.data import setup_data
    setup_data()
