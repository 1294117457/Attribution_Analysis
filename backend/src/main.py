"""FastAPI 应用入口"""

import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request

from shared.infrastructure.config.settings import get_settings
from shared.infrastructure.config.di import (
    build_collect_context,
    get_collect_manage_service,
    set_scheduler,
    setup_default_registry,
)
from shared.infrastructure.persistence.connection import async_engine, close_db
from contexts.collect.application.service.collect_manage_service import cancel_background
from contexts.collect.infrastructure.adapter.scheduler.apscheduler_adapter import ApschedulerAdapter
from contexts.collect.application.collect.tasks import all_collect_tasks
from contexts.collect.application.collect import setup_collect
from shared.interface.router_compat import api_router
from contexts.auth.infrastructure.security import key_manager
from app.exception_handler import register_exception_handlers
from app.middleware import register_middlewares

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

    # 注：表结构初始化已不再自动执行。请手动执行 backend/init.sql 建表。
    # 注：默认池/初始 admin 不再自动创建，请通过业务接口或手工 SQL 初始化。
    # 注：sys_collect_tasks 的 running 孤儿清理已下放到业务层
    #   （collect_manage_service.prepare → SqlCollectTaskStore.mark_running_as_failed），
    #   由用户下次发起同类型采集时处理，不再在启动时全局清扫。

    # 注册数据源到采集器注册中心
    setup_default_registry()

    # 组装 CollectContext（gateway / 4 个 IO 端口 / Service 工厂 / 并发）
    ctx = build_collect_context()

    # 注册采集任务到 CollectTaskRegistry（23 个：14 声明式 + 日 K + 股票清单 + 5 概念 + 2 占位）
    setup_collect(ctx, all_collect_tasks())

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


async def _sync_fetcher_catalog() -> None:
    """启动时用代码注册表对账 collect_fetchers 表

    - 代码有 / DB 无 → 自动 INSERT（补录）
    - DB 有 / 代码无 → 标 status='orphan'（**不删**，保留现场 + 避免 CASCADE 掉方案项）
    - 两边都有但元数据变了 → UPDATE + warning

    ⚠️ 必须在 setup_default_registry / setup_collect 之后调用。
    """
    from contexts.collect.application.collect import get_collect_task_registry
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

    for q in registry.realtime_ports():
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


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    application = FastAPI(
        title="智能金融数据归因分析平台",
        description="DDD 架构 - 数据采集 + K线查询",
        version="2.0.0",
        lifespan=lifespan,
    )

    register_middlewares(application)
    register_exception_handlers(application)
    application.include_router(api_router)
    return application


application = create_app()


@application.get("/health", tags=["系统"])
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
        "main:application",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
