"""FastAPI 应用入口"""

import json
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
from infrastructure.config.di import (
    get_collect_manage_service,
    set_scheduler,
    setup_default_registry,
)
from infrastructure.persistence.connection import async_engine, close_db
# 注册全部 ORM 模型（schema_init 用 Base.metadata 比对 init.sql）
import infrastructure.persistence.models  # noqa: F401
from infrastructure.persistence.schema_init import ensure_schema
from application.service import cancel_background
from infrastructure.adapter.scheduler.apscheduler_adapter import ApschedulerAdapter
from infrastructure.adapter.collect import (
    ConceptIndexTHCollectTask,
    ConceptListCollectTask,
    ConceptMembershipCollectTask,
    ConceptReasonCollectTask,
    ConceptSnapshotCollectTask,
    DailyBasicCollectTask,
    DailyKlineCollectTask,
    FinReportCollectTask,
    FinTop10HoldersCollectTask,
    FinTop10FloatHoldersCollectTask,
    StockBasicCollectTask,
    BaseAdjFactorCollectTask,
    BaseSuspendCollectTask,
    BaseNameChangeCollectTask,
    BaseDividendCollectTask,
    CapMoneyflowCollectTask,
    CapMarginDetailCollectTask,
    CapTopListCollectTask,
    CapTopInstCollectTask,
    CapBlockTradeCollectTask,
    CapHolderNumCollectTask,
    all_planned_tasks,
    setup_collect_task_registry,
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

    # 表结构：全新库按 backend/init.sql 建表，已有库只校验差异
    await ensure_schema()

    # 运行时清理：把上次异常退出遗留的 running/pending 任务标为 failed
    async with async_engine.begin() as conn:
        await _cleanup_stale_tasks(conn)
        await _ensure_default_pool(conn)
        await _ensure_initial_admin(conn)

    # 注册数据源到采集器注册中心
    setup_default_registry()

    # 注册采集任务到 CollectTaskRegistry（router 通过 get_collect_task_registry 读取）
    setup_collect_task_registry([
        # ── 已实现的基础任务（4 个）──
        DailyKlineCollectTask(),
        DailyBasicCollectTask(),
        StockBasicCollectTask(),
        FinReportCollectTask(),
        # ── 概念（adata · 同花顺，5 个：清单 / 成分股 / 日 K / 入选理由 / 快照）──
        ConceptListCollectTask(),
        ConceptMembershipCollectTask(),
        ConceptIndexTHCollectTask(),
        ConceptReasonCollectTask(),
        ConceptSnapshotCollectTask(),
        # ── 资金面（6 个，⭐⭐⭐ 0 → 6 突破）──
        CapMoneyflowCollectTask(),
        CapMarginDetailCollectTask(),
        CapTopListCollectTask(),
        CapTopInstCollectTask(),
        CapBlockTradeCollectTask(),
        CapHolderNumCollectTask(),
        # ── 基本面深度 / 基础层（5 个）──
        FinTop10HoldersCollectTask(),
        FinTop10FloatHoldersCollectTask(),
        BaseDividendCollectTask(),
        BaseAdjFactorCollectTask(),
        BaseSuspendCollectTask(),
        BaseNameChangeCollectTask(),
        # ── 剩余 planned（2 个：分钟 K 入库版 + news_article 权限未开通）──
        *all_planned_tasks(),
    ])

    # 对账 DB 侧的 collect_fetchers（采集任务 + 声明了 cache 的实时 Port，必须在注册之后）
    await _sync_fetcher_catalog()

    scheduler: ApschedulerAdapter | None = None
    if settings.COLLECT_SCHEDULER_ENABLED:
        scheduler = ApschedulerAdapter(settings.COLLECT_SCHEDULER_TIMEZONE)
        set_scheduler(scheduler)
        scheduler.on_fire(lambda payload: get_collect_manage_service().handle_job(payload))
        count = await get_collect_manage_service().restore_schedules()
        scheduler.start()
        logging.info("采集调度器已启动: %d 个方案", count)
    else:
        logging.info("采集调度器未启用（COLLECT_SCHEDULER_ENABLED=false）")

    yield

    if scheduler is not None:
        scheduler.shutdown()
        set_scheduler(None)
    await cancel_background()
    await close_db()


async def _cleanup_stale_tasks(conn) -> None:
    """启动期清理：把上次异常退出遗留的 running/pending 任务标为 failed。

    单进程部署，启动时仍为 running 的一定是上次崩溃残留。
    不清理会导致同类采集任务被防重拦截。
    """
    from sqlalchemy import text
    try:
        await conn.execute(text(
            "UPDATE sys_collect_tasks SET status = 'failed', finished_at = NOW(), "
            "message = COALESCE(message, '') || ' [服务重启，任务中断]' "
            "WHERE status = 'running'"
        ))
    except Exception as e:
        logging.warning("sys_collect_tasks 清理跳过: %s", e)


async def _sync_fetcher_catalog() -> None:
    """启动时用代码注册表对账 collect_fetchers 表

    - 代码有 / DB 无 → 自动 INSERT（补录）
    - DB 有 / 代码无 → 标 status='orphan'（**不删**，保留现场 + 避免 CASCADE 掉方案项）
    - 两边都有但元数据变了 → UPDATE + warning

    ⚠️ 必须在 setup_default_registry / setup_collect_task_registry 之后调用。
    """
    from infrastructure.adapter.collect import get_collect_task_registry
    from infrastructure.adapter.collect.registry import realtime_ports
    from sqlalchemy import text

    registry = get_collect_task_registry()
    code_side: dict[str, dict] = {}

    for t in registry.supported_types():
        h = registry.get(t)
        code_side[t] = {
            "label": h.label or h.name,
            "facet": h.facet or "",
            "sub_facet": h.sub_facet or "",
            "description": h.description or "",
            "kind": "batch",
            "status": h.status or "ready",
            "default_params": dict(h.default_params),
            "supports_run_one": h.supports_collect_one,
            "sort_order": h.sort_order,
        }

    for q in realtime_ports():
        code_side[q.name] = {
            "label": q.label or q.name,
            "facet": q.facet or "",
            "sub_facet": q.sub_facet or "",
            "description": q.description or "",
            "kind": "realtime",
            "status": "ready",
            "default_params": dict(q.sample_params),
            "supports_run_one": False,
            "sort_order": q.sort_order,
        }

    inserted = updated = 0
    async with async_engine.begin() as conn:
        rows = (await conn.execute(
            text("SELECT task_type, label, description, facet, sub_facet, "
                 "kind, status, default_params, supports_run_one, sort_order "
                 "FROM collect_fetchers")
        )).mappings().all()
        db_side = {r["task_type"]: dict(r) for r in rows}

        for task_type, meta in code_side.items():
            old = db_side.get(task_type)
            if old is None:
                await conn.execute(text(
                    "INSERT INTO collect_fetchers "
                    "(task_type, label, facet, sub_facet, description, kind, status, "
                    " default_params, supports_run_one, sort_order, created_at, updated_at) "
                    "VALUES (:tt, :label, :facet, :sub_facet, :description, :kind, :status, "
                    "         CAST(:dp AS json), :sro, :so, NOW(), NOW())"
                ), {
                    "tt": task_type,
                    "label": meta["label"][:64],
                    "facet": meta["facet"][:32],
                    "sub_facet": meta["sub_facet"][:32],
                    "description": meta["description"][:255],
                    "kind": meta["kind"],
                    "status": meta["status"],
                    "dp": json.dumps(meta["default_params"], ensure_ascii=False),
                    "sro": meta["supports_run_one"],
                    "so": meta["sort_order"],
                })
                inserted += 1
                continue

            # 已有：比对可变字段，有变化才 UPDATE
            changed = [
                k for k in ("label", "facet", "sub_facet", "description", "kind",
                            "default_params", "supports_run_one", "sort_order")
                if old.get(k) != meta[k]
            ]
            if old.get("status") == "orphan":
                changed.append("status")   # orphan 复活
            if not changed:
                continue

            await conn.execute(text(
                "UPDATE collect_fetchers SET label=:label, facet=:facet, sub_facet=:sub_facet, "
                "description=:description, kind=:kind, status=:status, "
                "default_params=CAST(:dp AS json), supports_run_one=:sro, sort_order=:so, "
                "updated_at=NOW() WHERE task_type=:tt"
            ), {
                "tt": task_type,
                "label": meta["label"][:64],
                "facet": meta["facet"][:32],
                "sub_facet": meta["sub_facet"][:32],
                "description": meta["description"][:255],
                "kind": meta["kind"],
                "status": meta["status"],
                "dp": json.dumps(meta["default_params"], ensure_ascii=False),
                "sro": meta["supports_run_one"],
                "so": meta["sort_order"],
            })
            updated += 1
            if old.get("status") == "orphan":
                logging.info("collect_fetchers %s 从 orphan 复活", task_type)
            else:
                logging.warning(
                    "collect_fetchers %s 元数据与代码不一致，已按代码更新: %s",
                    task_type, changed,
                )

        # DB 有 / 代码无 → orphan
        orphans = [t for t in db_side if t not in code_side]
        for task_type in orphans:
            await conn.execute(text(
                "UPDATE collect_fetchers SET status='orphan', updated_at=NOW() "
                "WHERE task_type=:tt AND status <> 'orphan'"
            ), {"tt": task_type})

    if orphans:
        logging.warning(
            "collect_fetchers 中有 %d 个接口在代码里已不存在，已标 orphan（未删除）: %s",
            len(orphans), orphans,
        )
    logging.info("collect_fetchers 对账完成: 新增 %d / 更新 %d / orphan %d / 共 %d",
                 inserted, updated, len(orphans), len(code_side))


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
        # 兜底：把 ctx/input 里的 bytes 转成 str，避免 JSON 序列化失败
        def _safe(value):
            if isinstance(value, bytes):
                try:
                    return value.decode("utf-8", errors="replace")
                except Exception:  # noqa: BLE001
                    return repr(value)
            if isinstance(value, dict):
                return {k: _safe(v) for k, v in value.items()}
            if isinstance(value, (list, tuple)):
                return [_safe(v) for v in value]
            return value

        return JSONResponse(
            status_code=422,
            content={
                "code": 422,
                "message": "请求参数校验失败",
                "data": {"errors": _safe(exc.errors())},
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

    # ⚠️ reload=True 未指定 reload_dirs，WatchFiles 会监听整个工作目录（backend/）。
    #    在 backend/ 内写任何文件（临时脚本、.log、采集输出）都会触发热重载，
    #    后端重启时正在跑的后台采集任务会被 asyncio.CancelledError 杀掉，
    #    表现为 sys_collect_tasks 里 status=cancelled 但 success=0，
    #    且日志无任何 fetcher 调用记录。详见 docs/overview/00-项目索引.md §8。
    #    如需在开发期跑长时采集任务，请改用 reload=False 启动，或把产物写到 backend/ 之外。
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
