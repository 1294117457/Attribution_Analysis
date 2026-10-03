"""依赖注入（DI）工厂

为 FastAPI route 层提供 application service 的 Depends 工厂。
DDD 改造核心：把 Repo/Service 构造从 application 层挪到 infrastructure，
application 层只接收已构造好的依赖（依赖反转）。

约定：
- 所有 AppService 工厂都集中在此；route 层只 Depends(...)
- scheduler / 后台任务走 `build_*_app_service(session)` 显式工厂（带 session 注入仓储）
- Fetcher 注册中心在 `setup_default_registry()` 内部注入（lifespan 时调用）

用法（route 层）：
    from infrastructure.config.di import get_kline_app_service

    @router.post("/kline/collect")
    async def collect(
        req: KlineCollectRequest,
        service: KlineAppService = Depends(get_kline_app_service),
    ):
        ...

用法（scheduler / 后台任务）：
    from infrastructure.config.di import build_kline_app_service

    async with AsyncSessionLocal() as session:
        svc = build_kline_app_service(session)
        ...
"""
from __future__ import annotations

import logging

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from application.port.collector_port import ConceptFetcher, KlineFetcher
from application.port.registry import get_registry
from application.service.auth_app_service import AuthAppService
from application.service.concept_app_service import ConceptAppService
from application.service.kline_app_service import KlineAppService
from application.service.panel_app_service import StockPanelAppService
from application.service.pool_app_service import StockPoolAppService
from application.service.pool_operation_app_service import PoolOperationAppService
from application.service.stock_analysis_app_service import StockAnalysisAppService
from application.service.stock_app_service import StockAppService
from domain.service import (
    ConceptBriefService,
    ConceptCollectionPolicy,
    IndicatorCalculator,
)
from infrastructure.persistence.connection import get_db
from infrastructure.persistence.repositories.auth_repository import (
    PermissionRepoImpl,
    RefreshTokenRepoImpl,
    RoleRepoImpl,
    UserRepoImpl,
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
from infrastructure.adapter.auth_port_adapters import (
    BcryptPasswordHasher,
    CaptchaAdapter,
    EmailVerificationAdapter,
    JwtAdapter,
)

logger = logging.getLogger(__name__)


# ── 通用领域服务（无 IO，可单例） ─────────────────────────────────────────────


def get_indicator_calculator() -> IndicatorCalculator:
    """IndicatorCalculator 单例（无状态，可复用）"""
    return IndicatorCalculator()


def get_concept_brief_service() -> ConceptBriefService:
    """概念摘要领域服务（无 IO，可单例）"""
    return ConceptBriefService()


def get_concept_collection_policy() -> ConceptCollectionPolicy:
    """概念采集保护策略（无状态，可单例）"""
    return ConceptCollectionPolicy()


# ── Fetcher（注册中心取） ────────────────────────────────────────────────────


def get_kline_fetcher() -> KlineFetcher:
    """K线 fetcher（从注册中心取）"""
    return get_registry().get(KlineFetcher)


# ── Auth 端口工厂 ───────────────────────────────────────────────────────────


def get_password_hasher() -> BcryptPasswordHasher:
    return BcryptPasswordHasher()


def get_jwt_service() -> JwtAdapter:
    return JwtAdapter()


def get_captcha() -> CaptchaAdapter:
    return CaptchaAdapter()


def get_email_verification_store() -> EmailVerificationAdapter:
    return EmailVerificationAdapter()


def get_permission_service(
    session: AsyncSession = Depends(get_db),
) -> None:
    """权限服务占位（保留向后兼容）"""
    raise RuntimeError("get_permission_service 已迁移, 请直接使用 AuthAppService")


# ── Route 层 Depends 工厂 ───────────────────────────────────────────────────


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


def get_stock_app_service(
    session: AsyncSession = Depends(get_db),
) -> StockAppService:
    """股票应用服务（CRUD + 元数据）"""
    return StockAppService(
        repo=StockRepoImpl(session),
    )


def get_concept_app_service(
    session: AsyncSession = Depends(get_db),
) -> ConceptAppService:
    """概念应用服务（查询 + 实时反查）"""
    registry = get_registry()
    if not registry.has(ConceptFetcher):
        from fastapi import HTTPException
        raise HTTPException(503, "概念采集器未注册")
    return ConceptAppService(
        repo=ConceptRepoImpl(session),
        fetcher=registry.get(ConceptFetcher),
    )


def get_panel_app_service(
    session: AsyncSession = Depends(get_db),
    brief_service: ConceptBriefService = Depends(get_concept_brief_service),
) -> StockPanelAppService:
    """Panel 应用服务 — 注入 concept repo + panel compose repo + brief service"""
    return StockPanelAppService(
        panel_repo=StockPanelComposeRepoImpl(session),
        concept_repo=ConceptRepoImpl(session),
        brief_service=brief_service,
    )


def get_pool_app_service(
    session: AsyncSession = Depends(get_db),
) -> StockPoolAppService:
    """操作池应用服务（CRUD + 成员管理）"""
    return StockPoolAppService(
        pool_repo=StockPoolRepoImpl(session),
        stock_repo=StockRepoImpl(session),
    )


def get_pool_operation_app_service(
    session: AsyncSession = Depends(get_db),
) -> PoolOperationAppService:
    """池操作应用服务（后台派发 + 进度查询）"""
    from infrastructure.adapter.scheduler.operation_dispatcher import (
        OperationDispatcher,
    )
    return PoolOperationAppService(
        pool_repo=StockPoolRepoImpl(session),
        op_repo=PoolOperationRepoImpl(session),
        dispatcher=OperationDispatcher(),
    )


def get_stock_analysis_app_service(
    session: AsyncSession = Depends(get_db),
) -> StockAnalysisAppService:
    """股票归因分析服务（聚合视图，AI 入口）"""
    return StockAnalysisAppService(
        stock_repo=StockRepoImpl(session),
        kline_repo=KlineRepoImpl(session),
        pool_repo=StockPoolRepoImpl(session),
    )


def get_auth_app_service(
    session: AsyncSession = Depends(get_db),
    hasher: BcryptPasswordHasher = Depends(get_password_hasher),
    jwt: JwtAdapter = Depends(get_jwt_service),
    captcha: CaptchaAdapter = Depends(get_captcha),
    email_store: EmailVerificationAdapter = Depends(get_email_verification_store),
) -> AuthAppService:
    """认证授权应用服务 — 注入 ports + repos"""
    return AuthAppService(
        users=UserRepoImpl(session),
        roles=RoleRepoImpl(session),
        perms=PermissionRepoImpl(session),
        refresh=RefreshTokenRepoImpl(),
        hasher=hasher,
        captcha=captcha,
        email_verify=email_store,
        jwt=jwt,
    )


# ── Scheduler 工厂（带 session 参数的同步构造版）─────────────────────────────


def build_kline_app_service(session: AsyncSession) -> KlineAppService:
    """为后台任务构造 KlineAppService（同步传 session）"""
    return KlineAppService(
        kline_repo=KlineRepoImpl(session),
        stock_repo=StockRepoImpl(session),
        indicator_calc=IndicatorCalculator(),
    )


def build_stock_app_service(session: AsyncSession) -> StockAppService:
    return StockAppService(repo=StockRepoImpl(session))


def build_concept_app_service(session: AsyncSession) -> ConceptAppService:
    registry = get_registry()
    return ConceptAppService(
        repo=ConceptRepoImpl(session),
        fetcher=registry.get(ConceptFetcher),
    )


# ── Fetcher 注册中心初始化 ──────────────────────────────────────────────────


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