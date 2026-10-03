"""依赖注入（DI）工厂

为 FastAPI route 层提供 application service 的 Depends 工厂。
DDD 改造核心：把 Repo/Service 构造从 application 层挪到 infrastructure，
application 层只接收已构造好的依赖（依赖反转）。

约定：
- 所有 service 工厂都集中在此；route 层只 Depends(...)
- scheduler / 后台任务走 `build_*_service(session)` 显式工厂（带 session 注入仓储）
- Fetcher 注册中心在 `setup_default_registry()` 内部注入（lifespan 时调用）

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
from typing import TYPE_CHECKING, AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from application.port.collector_port import ConceptFetcher, KlineFetcher
from application.port.registry import get_registry
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
from infrastructure.adapter.realtime.framework import get_realtime_query_framework
from infrastructure.adapter.realtime.registry import get_realtime_registry

if TYPE_CHECKING:
    # 仅供 type hint,避免循环 import
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
    """概念摘要领域服务（无 IO，可单例）"""
    return ConceptBriefService()


def get_concept_collection_policy() -> ConceptCollectionPolicy:
    """概念采集保护策略（无状态，可单例）"""
    return ConceptCollectionPolicy()


# ═══════════════════════════════════════════════════════════════════════════════
#  Fetcher（注册中心取）
# ═══════════════════════════════════════════════════════════════════════════════


def get_kline_fetcher() -> KlineFetcher:
    """K线 fetcher（从注册中心取）"""
    return get_registry().get(KlineFetcher)


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
#  CollectManage 端口适配
# ═══════════════════════════════════════════════════════════════════════════════


@asynccontextmanager
async def _session_ctx() -> AsyncIterator[AsyncSession]:
    """Session 工厂（适配 CollectManageService 的 SessionFactoryPort）"""
    async with AsyncSessionLocal() as session:
        yield session


def _get_collect_redis():
    """Redis 端口（适配 CollectManageService 的 RedisPort）"""
    from infrastructure.adapter.cache.redis_client import get_redis
    return get_redis()


def _get_collect_task_registry():
    """采集任务注册中心（lazy import 避免循环依赖）"""
    from infrastructure.adapter.scheduler.collect import get_collect_task_registry as _gtr
    return _gtr()


def _get_collect_scheduler():
    """采集调度器（lazy import 避免循环依赖）"""
    from infrastructure.adapter.scheduler.collect_scheduler import get_collect_scheduler as _gcs
    return _gcs()


def _get_realtime_registry():
    """实时接口注册中心"""
    return get_realtime_registry()


def get_collect_manage_service() -> "CollectManageService":
    """采集管理应用服务（依赖注入）"""
    from application.service import CollectManageService
    return CollectManageService(
        redis=_get_collect_redis(),
        task_registry=_get_collect_task_registry(),
        scheduler=_get_collect_scheduler(),
        config_repo=CollectConfigRepoImpl(None),  # noqa: session 内部自开
        realtime_registry=_get_realtime_registry(),
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
    )


def get_concept_service(
    session: AsyncSession = Depends(get_db),
) -> "ConceptService":
    """概念基础查询服务（共享）"""
    from application.service import ConceptService
    registry = get_registry()
    if not registry.has(ConceptFetcher):
        from fastapi import HTTPException
        raise HTTPException(503, "概念采集器未注册")
    return ConceptService(
        repo=ConceptRepoImpl(session),
        fetcher=registry.get(ConceptFetcher),
        realtime=get_realtime_query_framework(),
    )


def get_concept_board_service(
    session: AsyncSession = Depends(get_db),
) -> "ConceptBoardService":
    """概念大盘应用服务（大盘 + 概念 K 线）"""
    from application.service import ConceptBoardService
    return ConceptBoardService(
        repo=ConceptRepoImpl(session),
        realtime=get_realtime_query_framework(),
    )


def get_stock_pool_service(
    session: AsyncSession = Depends(get_db),
) -> "StockPoolService":
    """操作池应用服务（CRUD + 成员 + 池操作派发）"""
    from application.service import StockPoolService
    from infrastructure.adapter.scheduler.operation_dispatcher import (
        OperationDispatcher,
    )
    return StockPoolService(
        pool_repo=StockPoolRepoImpl(session),
        stock_repo=StockRepoImpl(session),
        op_repo=PoolOperationRepoImpl(session),
        dispatcher=OperationDispatcher(),
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Scheduler 工厂（带 session 参数的同步构造版）
# ═══════════════════════════════════════════════════════════════════════════════


def build_stock_info_service(session: AsyncSession) -> "StockInfoService":
    """为后台任务构造 StockInfoService（仅 K 线采集任务需要）"""
    from application.service import StockInfoService
    return StockInfoService(
        stock_repo=StockRepoImpl(session),
        kline_repo=KlineRepoImpl(session),
        pool_repo=StockPoolRepoImpl(session),
        panel_repo=StockPanelComposeRepoImpl(session),
        concept_repo=ConceptRepoImpl(session),
        brief_service=ConceptBriefService(),
        indicator_calc=IndicatorCalculator(),
    )


def build_concept_service(session: AsyncSession) -> "ConceptService":
    """为后台任务构造 ConceptService（采集任务 / 反查）"""
    from application.service import ConceptService
    registry = get_registry()
    return ConceptService(
        repo=ConceptRepoImpl(session),
        fetcher=registry.get(ConceptFetcher),
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Fetcher 注册中心初始化
# ═══════════════════════════════════════════════════════════════════════════════


def setup_default_registry() -> None:
    """构造 Fetcher 实例并注册到全局注册中心

    调用时机：FastAPI lifespan 启动时。
    本函数只由 infrastructure 层持有（application 不知道 SDK 细节）。
    """
    from application.port.collector_port import (
        ConceptFetcher,
        DailyBasicFetcher,
        FinReportFetcher,
        KlineFetcher,
        MinuteKlineFetcher,
        StockBasicFetcher,
    )
    from infrastructure.adapter.fetcher.pytdx import PytdxFetcher
    from infrastructure.adapter.fetcher.tushare import TushareFetcher
    from route.dto.request.kline import KlineBO

    reg = get_registry()

    # ── TushareFetcher：覆盖 Kline / StockBasic / DailyBasic / FinReport ──
    tushare_singleton = TushareFetcher(KlineBO)
    tushare_factory = lambda: TushareFetcher(KlineBO)  # noqa: E731

    reg.register_instance(KlineFetcher, tushare_singleton)
    reg.register_factory(KlineFetcher, tushare_factory)
    reg.register_instance(StockBasicFetcher, tushare_singleton)
    reg.register_factory(StockBasicFetcher, tushare_factory)
    reg.register_instance(DailyBasicFetcher, tushare_singleton)
    reg.register_factory(DailyBasicFetcher, tushare_factory)
    reg.register_instance(FinReportFetcher, tushare_singleton)

    # ── MinuteKlineFetcher（PytdxFetcher 有状态，单例复用 TCP 连接） ──
    pytdx_fetcher = PytdxFetcher()
    reg.register_instance(MinuteKlineFetcher, pytdx_fetcher)
    reg.register_factory(MinuteKlineFetcher, PytdxFetcher)

    # ── ConceptFetcher（adata 优先，缺包时降级） ──
    try:
        from infrastructure.adapter.fetcher.adata import AdataConceptFetcher
        reg.register_instance(ConceptFetcher, AdataConceptFetcher())
        reg.register_factory(ConceptFetcher, AdataConceptFetcher)
    except Exception as e:
        logger.warning("ConceptFetcher (Adata) 未注册: %s", e)

    logger.info("FetcherRegistry 初始化完成: %s", reg)
