"""FastAPI 应用入口"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from domain.base import DomainError
from domain.entitys.kline.entity import (
    CollectionError,
    KlineDataError,
    KlineNotFoundError,
)
from domain.entitys.stock_info.entity import StockNotFoundError
from domain.entitys.stock_pool.entity import (
    DuplicateMemberError,
    MemberNotFoundError,
    PoolNotFoundError,
    PoolOperationConflictError,
    PoolOperationNotFoundError,
    CannotDeleteDefaultPoolError,
)
from infrastructure.config.settings import get_settings
from application.port.registry import setup_default_registry
from infrastructure.persistence.base import Base
from infrastructure.persistence.connection import async_engine, close_db
# ORM 模型导入（仅用于触发模型注册，Base.metadata.create_all 会扫描所有继承 Base 的类）
from infrastructure.persistence.models import (                                            # noqa: F401
    TechKlineDailyDB,
    StockInfoDB,
    StockPoolDB,
    StockPoolMemberDB,
    PoolOperationDB,
    FinReportDB,
    FinDailyBasicDB,
    CapMarginDB,
    CapMoneyflowDB,
    CapMarginDetailDB,
    CapTopListDB,
    CapTopInstDB,
    CapBlockTradeDB,
    CapHolderNumDB,
    FinTop10HolderDB,
    FinTop10FloatHolderDB,
    BaseAdjFactorDB,
    BaseDividendDB,
    BaseSuspendDB,
    BaseNameChangeDB,
    MktCalendarDB,
    MktMarketDailyDB,
    MktSectorDailyDB,
    MktIndexMemberDB,
    ConceptsDB,
    ConceptMemberDB,
    ConceptIndexTHDB,
    ConceptSnapshotDB,
    CollectPlanDB,
    CollectGroupDB,
)
from application.service.collect_app_service import cancel_background
from infrastructure.adapter.scheduler.collect_scheduler import (
    start_collect_scheduler,
    stop_collect_scheduler,
)
from infrastructure.adapter.scheduler.collect import (
    ConceptIndexTHCollectTask,
    ConceptListCollectTask,
    ConceptMembershipCollectTask,
    DailyBasicCollectTask,
    DailyKlineCollectTask,
    FinReportCollectTask,
    StockBasicCollectTask,
    all_planned_tasks,
    setup_collect_task_registry,
)
from infrastructure.adapter.realtime import (
    ConceptMinuteQuery,
    StockMinuteKlineQuery,
    setup_realtime_registry,
)
from route.api.router import api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期管理"""
    async with async_engine.begin() as conn:
        # 先做重命名 / 重建（必须在 create_all 之前，否则 create_all 会创建空的新表）
        await _migrate_rename_kline_table(conn)
        await _migrate_concepts_adata_rebuild(conn)
        await conn.run_sync(Base.metadata.create_all)
        # 兼容旧表：补齐 stock_infos 新增字段（仅首次启动时执行）
        await _migrate_stock_infos(conn)
        # 兼容旧 daily_klines：补齐 17 个技术指标列（针对旧表）
        await _migrate_daily_klines_indicators(conn)
        await _migrate_sys_collect_tasks(conn)
        # 初始化操作池：创建默认池
        await _ensure_default_pool(conn)

    # 注册数据源到采集器注册中心
    setup_default_registry()

    # 注册采集任务到 CollectTaskRegistry（router 通过 get_collect_task_registry 读取）
    setup_collect_task_registry([
        DailyKlineCollectTask(),
        DailyBasicCollectTask(),
        StockBasicCollectTask(),
        FinReportCollectTask(),
        # 概念（adata · 同花顺），依赖顺序：清单 → 成分股；清单 → 日 K
        ConceptListCollectTask(),
        ConceptMembershipCollectTask(),
        ConceptIndexTHCollectTask(),
        # 🆕 四面重构：14 个 planned 占位任务（资金面/基础层/基本面深度/新闻面）
        *all_planned_tasks(),
    ])
    # 实时接口（按需查询 + Redis 缓存，与采集任务共用目录）
    setup_realtime_registry([ConceptMinuteQuery(), StockMinuteKlineQuery()])

    if settings.COLLECT_SCHEDULER_ENABLED:
        await start_collect_scheduler(settings.COLLECT_SCHEDULER_TIMEZONE)
    else:
        logging.info("采集调度器未启用（COLLECT_SCHEDULER_ENABLED=false）")

    yield

    stop_collect_scheduler()
    await cancel_background()
    await close_db()


async def _migrate_sys_collect_tasks(conn) -> None:
    """sys_collect_tasks 补 group_run_id 列（采集任务组）"""
    from sqlalchemy import text
    statements = [
        "ALTER TABLE sys_collect_tasks ADD COLUMN IF NOT EXISTS group_run_id INTEGER",
        "CREATE INDEX IF NOT EXISTS ix_sys_collect_tasks_group_run_id ON sys_collect_tasks (group_run_id)",
        # 单进程部署：启动时仍为 running 的是上次进程异常退出遗留，不清理会让同类任务（含定时）永远被防重拦截
        "UPDATE sys_collect_tasks SET status = 'failed', finished_at = NOW(), "
        "message = COALESCE(message, '') || ' [服务重启，任务中断]' WHERE status = 'running'",
    ]
    for stmt in statements:
        try:
            await conn.execute(text(stmt))
        except Exception as e:
            logging.warning("sys_collect_tasks 迁移跳过: %s | %s", stmt, e)


async def _migrate_rename_kline_table(conn) -> None:
    """将旧表 daily_klines 重命名为 tech_kline_dailys

    使用 IF EXISTS 保证幂等，可重复执行。
    """
    from sqlalchemy import text
    rename_statements = [
        "ALTER TABLE IF EXISTS daily_klines RENAME TO tech_kline_dailys",
        "ALTER INDEX IF EXISTS uq_kline_symbol_date RENAME TO uq_tech_kline_symbol_date",
        "ALTER INDEX IF EXISTS ix_kline_symbol_date RENAME TO ix_tech_kline_symbol_date",
    ]
    for stmt in rename_statements:
        try:
            await conn.execute(text(stmt))
        except Exception as e:
            logging.warning("kline 表重命名跳过: %s | %s", stmt, e)


async def _migrate_daily_klines_indicators(conn) -> None:
    """兼容旧 schema：为已存在的 tech_kline_dailys 表添加 17 个技术指标列

    字段全部为可空 Float 列, IF NOT EXISTS 保证幂等。
    PostgreSQL 11+ ADD COLUMN 不锁表, 直接执行即可。
    """
    from sqlalchemy import text
    indicator_columns = [
        # 均线
        "ALTER TABLE tech_kline_dailys ADD COLUMN IF NOT EXISTS ma5 DOUBLE PRECISION",
        "ALTER TABLE tech_kline_dailys ADD COLUMN IF NOT EXISTS ma10 DOUBLE PRECISION",
        "ALTER TABLE tech_kline_dailys ADD COLUMN IF NOT EXISTS ma20 DOUBLE PRECISION",
        "ALTER TABLE tech_kline_dailys ADD COLUMN IF NOT EXISTS ma60 DOUBLE PRECISION",
        # EMA
        "ALTER TABLE tech_kline_dailys ADD COLUMN IF NOT EXISTS ema12 DOUBLE PRECISION",
        "ALTER TABLE tech_kline_dailys ADD COLUMN IF NOT EXISTS ema26 DOUBLE PRECISION",
        # MACD
        "ALTER TABLE tech_kline_dailys ADD COLUMN IF NOT EXISTS macd_dif DOUBLE PRECISION",
        "ALTER TABLE tech_kline_dailys ADD COLUMN IF NOT EXISTS macd_dea DOUBLE PRECISION",
        "ALTER TABLE tech_kline_dailys ADD COLUMN IF NOT EXISTS macd_bar DOUBLE PRECISION",
        # RSI
        "ALTER TABLE tech_kline_dailys ADD COLUMN IF NOT EXISTS rsi6 DOUBLE PRECISION",
        "ALTER TABLE tech_kline_dailys ADD COLUMN IF NOT EXISTS rsi12 DOUBLE PRECISION",
        "ALTER TABLE tech_kline_dailys ADD COLUMN IF NOT EXISTS rsi24 DOUBLE PRECISION",
        # KDJ
        "ALTER TABLE tech_kline_dailys ADD COLUMN IF NOT EXISTS kdj_k DOUBLE PRECISION",
        "ALTER TABLE tech_kline_dailys ADD COLUMN IF NOT EXISTS kdj_d DOUBLE PRECISION",
        "ALTER TABLE tech_kline_dailys ADD COLUMN IF NOT EXISTS kdj_j DOUBLE PRECISION",
        # BOLL
        "ALTER TABLE tech_kline_dailys ADD COLUMN IF NOT EXISTS boll_up DOUBLE PRECISION",
        "ALTER TABLE tech_kline_dailys ADD COLUMN IF NOT EXISTS boll_mid DOUBLE PRECISION",
        "ALTER TABLE tech_kline_dailys ADD COLUMN IF NOT EXISTS boll_dn DOUBLE PRECISION",
    ]
    for stmt in indicator_columns:
        try:
            await conn.execute(text(stmt))
        except Exception as e:
            logging.warning("tech_kline_dailys 指标迁移跳过: %s | %s", stmt, e)


async def _migrate_stock_infos(conn) -> None:
    """兼容旧 schema：为已存在的 stock_infos 表添加新增字段

    字段：ts_code / area / exchange / delist_date / list_status / is_hs
    全部为可空列，IF NOT EXISTS 保证幂等。
    """
    from sqlalchemy import text
    statements = [
        "ALTER TABLE stock_infos ADD COLUMN IF NOT EXISTS ts_code VARCHAR(20)",
        "ALTER TABLE stock_infos ADD COLUMN IF NOT EXISTS area VARCHAR(50)",
        "ALTER TABLE stock_infos ADD COLUMN IF NOT EXISTS exchange VARCHAR(10)",
        "ALTER TABLE stock_infos ADD COLUMN IF NOT EXISTS delist_date DATE",
        "ALTER TABLE stock_infos ADD COLUMN IF NOT EXISTS list_status VARCHAR(5) DEFAULT 'L'",
        "ALTER TABLE stock_infos ADD COLUMN IF NOT EXISTS is_hs VARCHAR(5) DEFAULT 'N'",
        "CREATE INDEX IF NOT EXISTS ix_stock_infos_ts_code ON stock_infos (ts_code)",
        "CREATE INDEX IF NOT EXISTS ix_stock_infos_area ON stock_infos (area)",
        "CREATE INDEX IF NOT EXISTS ix_stock_infos_exchange ON stock_infos (exchange)",
        "CREATE INDEX IF NOT EXISTS ix_stock_infos_list_status ON stock_infos (list_status)",
        "ALTER TABLE stock_infos ADD COLUMN IF NOT EXISTS act_name VARCHAR(200)",
        "ALTER TABLE stock_infos ADD COLUMN IF NOT EXISTS act_ent_type VARCHAR(50)",
    ]
    for stmt in statements:
        try:
            await conn.execute(text(stmt))
        except Exception as e:
            logging.warning("迁移跳过（已存在或不支持）: %s | %s", stmt, e)


async def _migrate_concepts_adata_rebuild(conn) -> None:
    """概念表改为以同花顺 index_code 为业务键（04-概念数据adata同源改造方案 §4.1）

    concepts 已有表但没有 index_code 列 → 视为旧结构，删除 4 张概念表，
    交给随后的 create_all 按新 ORM 重建。旧数据不迁移，重建后重跑采集任务。
    """
    from sqlalchemy import text

    has_table = await conn.scalar(text("SELECT to_regclass('public.concepts') IS NOT NULL"))
    if not has_table:
        return
    has_index_code = await conn.scalar(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'concepts' AND column_name = 'index_code'"
    ))
    if has_index_code:
        return
    await conn.execute(text(
        "DROP TABLE IF EXISTS concept_snapshots, concept_index_ths, "
        "stock_concept_members, concepts CASCADE"
    ))
    logging.info("概念表为旧结构，已删除并交由 create_all 按 index_code 新结构重建")


async def _ensure_default_pool(conn) -> None:
    """确保存在默认操作池（首次启动）"""
    from sqlalchemy import text
    try:
        result = await conn.execute(
            text("SELECT COUNT(*) FROM stock_pools WHERE is_default = TRUE")
        )
        count = result.scalar()
        if count == 0:
            await conn.execute(
                text(
                    "INSERT INTO stock_pools "
                    "(name, pool_type, is_default, icon, color, sort_order, "
                    "is_archived, created_at, updated_at) "
                    "VALUES (:name, :type, TRUE, :icon, :color, 0, FALSE, NOW(), NOW())"
                ),
                {
                    "name": "我的自选",
                    "type": "watchlist",
                    "icon": "⭐",
                    "color": "#FFB800",
                },
            )
            logging.info("已创建默认池：我的自选")
    except Exception as e:
        logging.warning("默认池初始化跳过: %s", e)


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="智能金融数据归因分析平台",
        description="DDD 架构 - 数据采集 + K线查询",
        version="2.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router)
    return app


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器"""

    @app.exception_handler(KlineNotFoundError)
    async def kline_not_found(request: Request, exc: KlineNotFoundError):
        return JSONResponse(
            status_code=404,
            content={"code": 404, "message": exc.message, "data": None},
        )

    @app.exception_handler(StockNotFoundError)
    async def stock_not_found(request: Request, exc: StockNotFoundError):
        return JSONResponse(
            status_code=404,
            content={"code": 404, "message": exc.message, "data": None},
        )

    @app.exception_handler(KlineDataError)
    async def kline_data_error(request: Request, exc: KlineDataError):
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": exc.message, "data": None},
        )

    @app.exception_handler(CollectionError)
    async def collection_error(request: Request, exc: CollectionError):
        return JSONResponse(
            status_code=502,
            content={"code": 502, "message": exc.message, "data": None},
        )

    @app.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError):
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": exc.message, "data": None},
        )

    @app.exception_handler(PoolNotFoundError)
    async def pool_not_found(request: Request, exc: PoolNotFoundError):
        return JSONResponse(
            status_code=404,
            content={"code": 404, "message": exc.message, "data": None},
        )

    @app.exception_handler(PoolOperationNotFoundError)
    async def pool_op_not_found(request: Request, exc: PoolOperationNotFoundError):
        return JSONResponse(
            status_code=404,
            content={"code": 404, "message": exc.message, "data": None},
        )

    @app.exception_handler(PoolOperationConflictError)
    async def pool_op_conflict(request: Request, exc: PoolOperationConflictError):
        return JSONResponse(
            status_code=409,
            content={"code": 409, "message": exc.message, "data": None},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "code": 422,
                "message": "请求参数校验失败",
                "data": {"errors": exc.errors()},
            },
        )

    @app.exception_handler(ValueError)
    async def value_error(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": str(exc), "data": None},
        )

    @app.exception_handler(RuntimeError)
    async def runtime_error(request: Request, exc: RuntimeError):
        return JSONResponse(
            status_code=502,
            content={"code": 502, "message": str(exc), "data": None},
        )

    @app.exception_handler(KeyError)
    async def registry_not_found(request: Request, exc: KeyError):
        """注册中心未找到对应的协议实现（通常是启动配置缺失）"""
        logging.error("数据源未注册: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"code": 503, "message": f"数据源未配置: {exc}", "data": None},
        )

    @app.exception_handler(Exception)
    async def generic_error(request: Request, exc: Exception):
        logging.exception("未处理的异常: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": "服务器内部错误", "data": None},
        )


app = create_app()


@app.get("/health", tags=["系统"])
async def health():
    """健康检查"""
    return {"status": "ok", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
