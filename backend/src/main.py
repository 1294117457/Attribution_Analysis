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
from infrastructure.config.di import setup_default_registry
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
    # 认证授权 ORM 模型
    UserDB,                                                              # noqa: F401
    RoleDB,                                                              # noqa: F401
    PermissionDB,                                                        # noqa: F401
    UserRoleDB,                                                          # noqa: F401
    RolePermissionDB,                                                    # noqa: F401
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
from infrastructure.security import key_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期管理"""
    # JWT 密钥预热(第一次启动时生成 RSA 密钥对到 .keys/)
    key_manager.warmup()

    # 第一段事务:create_all(必须先建表,后续迁移依赖)
    async with async_engine.begin() as conn:
        # 先做重命名 / 重建(必须在 create_all 之前,否则 create_all 会创建空的新表)
        await _migrate_rename_kline_table(conn)
        await _migrate_concepts_adata_rebuild(conn)
        await conn.run_sync(Base.metadata.create_all)

    # 第二段事务:兼容旧表的列补齐、采集任务补丁、默认池、auth 系统
    # —— 拆出独立事务,避免单个迁移失败导致 create_all 回滚(这是 2026-10-03 排查的 bug)
    async with async_engine.begin() as conn:
        await _migrate_stock_infos(conn)
        await _migrate_daily_klines_indicators(conn)
        await _migrate_sys_collect_tasks(conn)
        await _ensure_default_pool(conn)
        await _migrate_auth_system(conn)
        await _ensure_initial_admin(conn)

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


async def _migrate_auth_system(conn) -> None:
    """加载 backend/migrations/*.sql 顺序执行,全部幂等。

    文件(数字前缀即执行顺序):
    - 002_auth_system.sql                     建 6 张 sys_* 表 + 角色/权限
    - 003_drop_username.sql                   删 sys_users.username 字段
    - 005_drop_redis_replaced_tables.sql      删 sys_email_verifications / sys_refresh_tokens / sys_captchas(已切到 Redis)

    关键:每条语句独立 SAVEPOINT,任意一条失败不会污染整个事务。
    注释行(-- 开头)被预过滤,避免被当成"坏 SQL"塞进事务。
    """
    from pathlib import Path
    from sqlalchemy import text

    # __file__ = .../backend/src/main.py
    # .parent.parent = backend/  ← migrations 目录在 backend/ 下
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    if not migrations_dir.exists():
        logging.warning("migrations 目录未找到: %s,跳过", migrations_dir)
        return

    files = [
        "001_add_role_perm_unique.sql",
        "002_auth_system.sql",
        "003_drop_username.sql",
        "005_drop_redis_replaced_tables.sql",
    ]
    for file_name in files:
        path = migrations_dir / file_name
        if not path.exists():
            logging.warning("%s 未找到: %s,跳过", file_name, path)
            continue
        sql = path.read_text(encoding="utf-8")

        # 过滤掉纯注释行 / 空行,只保留真正可执行的 SQL
        executable = []
        for raw_stmt in sql.split(";"):
            lines = [
                ln for ln in raw_stmt.splitlines()
                if ln.strip() and not ln.strip().startswith("--")
            ]
            cleaned = "\n".join(lines).strip()
            if cleaned:
                executable.append(cleaned)

        file_success = 0
        file_skip = 0
        for i, stmt in enumerate(executable, 1):
            savepoint = f"auth_mig_{file_name[:3]}_{i}".replace(".", "_")
            try:
                await conn.execute(text(f"SAVEPOINT {savepoint}"))
                await conn.execute(text(stmt))
                await conn.execute(text(f"RELEASE SAVEPOINT {savepoint}"))
                file_success += 1
            except Exception as e:  # noqa: BLE001
                file_skip += 1
                # 回滚到 savepoint 之前,事务可继续
                try:
                    await conn.execute(text(f"ROLLBACK TO SAVEPOINT {savepoint}"))
                except Exception:
                    pass
                logging.warning(
                    "auth %s 子句 #%d 跳过: %s | err=%s",
                    file_name, i, stmt[:80], e,
                )
        logging.info(
            "auth %s 迁移完成: success=%d skip=%d",
            file_name, file_success, file_skip,
        )


async def _ensure_initial_admin(conn) -> None:
    """首次启动时创建初始 admin 用户
    email=admin@local / password=admin123,
    并绑定 admin 角色。

    重启行为:
    - sys_users 为空 → INSERT 新账号
    - sys_users 不为空但无 admin@local → 跳过
    - admin@local 存在但密码不匹配(开发期间偶发,例如 bcrypt 升级) →
      用 ENV 变量 ATTR_REBUILD_ADMIN_HASH=true(默认) 强制重置 hash;
      生产环境可设 false 关闭
    """
    import bcrypt as _bcrypt
    import os
    from sqlalchemy import text

    target_email = "admin@local"
    target_password = b"admin123"
    rebuild = os.getenv("ATTR_REBUILD_ADMIN_HASH", "true").lower() != "false"

    try:
        existing = (await conn.execute(
            text("SELECT id, password_hash FROM sys_users WHERE email = :e"),
            {"e": target_email},
        )).first()
    except Exception as e:
        logging.warning("查询 sys_users 失败,跳过 admin 初始化: %s", e)
        return

    new_hash = _bcrypt.hashpw(target_password, _bcrypt.gensalt(rounds=12)).decode("utf-8")

    if existing is None:
        # INSERT
        try:
            admin_id = (
                await conn.execute(
                    text(
                        "INSERT INTO sys_users (email, password_hash, nickname, "
                        "is_active, is_verified) VALUES "
                        "(:e, :h, '系统管理员', TRUE, TRUE) RETURNING id"
                    ),
                    {"e": target_email, "h": new_hash},
                )
            ).scalar()
            await conn.execute(
                text(
                    "INSERT INTO sys_user_roles (user_id, role_id) "
                    "VALUES (:u, (SELECT id FROM sys_roles WHERE code = 'admin'))"
                ),
                {"u": admin_id},
            )
            logging.warning(
                "=" * 70 + "\n"
                "  初始 admin 账号已创建!\n"
                "    email    : %s\n"
                "    password : admin123\n"
                "  [WARNING]  请登录后第一时间修改!\n" + "=" * 70,
                target_email,
            )
        except Exception as e:
            logging.error("创建初始 admin 失败: %s", e)
        return

    # 已存在 — 校验 hash
    try:
        ok = _bcrypt.checkpw(target_password, existing.password_hash.encode("utf-8"))
    except Exception:
        ok = False
    if ok:
        logging.info("admin@local hash 校验通过,无需重置")
        return

    # hash 不匹配
    if not rebuild:
        logging.warning(
            "admin@local hash 校验失败,但 ATTR_REBUILD_ADMIN_HASH=false 跳过重置。"
            "请手动: UPDATE sys_users SET password_hash='%s' WHERE email='%s'",
            new_hash, target_email,
        )
        return

    logging.warning("admin@local hash 校验失败,自动重置为 admin123 (ATTR_REBUILD_ADMIN_HASH=true)")
    await conn.execute(
        text("UPDATE sys_users SET password_hash = :h WHERE id = :i"),
        {"h": new_hash, "i": existing.id},
    )


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
