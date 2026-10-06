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
    CollectPlanItemDB,
    CollectFetcherDB,
    # 认证授权 ORM 模型
    UserDB,                                                              # noqa: F401
    RoleDB,                                                              # noqa: F401
    PermissionDB,                                                        # noqa: F401
    UserRoleDB,                                                          # noqa: F401
    RolePermissionDB,                                                    # noqa: F401
)
from application.service import cancel_background
from infrastructure.adapter.scheduler.collect_scheduler import (
    start_collect_scheduler,
    stop_collect_scheduler,
)
from infrastructure.adapter.scheduler.collect import (
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
        # ⚠️ 以下两步顺序不可颠倒：
        #    ① _rebuild_collect_config_tables 删旧表（必须在 create_all 之前，
        #       否则 create_all 看到旧表会跳过，然后表被删掉 → 本次启动期间表缺失）
        #    ② create_all 按新 ORM 重建
        await _rebuild_collect_config_tables(conn)
        await _migrate_rename_kline_table(conn)
        await _migrate_concepts_adata_rebuild(conn)
        await conn.run_sync(Base.metadata.create_all)

    # 第二段事务:兼容旧表的列补齐、采集任务补丁、默认池、auth 系统
    # —— 拆出独立事务,避免单个迁移失败导致 create_all 回滚(这是 2026-10-03 排查的 bug)
    async with async_engine.begin() as conn:
        await _migrate_stock_infos(conn)
        await _migrate_daily_klines_indicators(conn)
        await _migrate_sys_collect_tasks(conn)
        await _rename_group_run_id_to_plan_run_id(conn)
        await _ensure_default_pool(conn)
        await _migrate_auth_system(conn)
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
    # 实时接口（按需查询 + Redis 缓存，与采集任务共用目录）
    setup_realtime_registry([ConceptMinuteQuery(), StockMinuteKlineQuery()])

    # 对账 DB 侧的 collect_fetchers（依赖上面两个注册表，必须在其后）
    await _sync_fetcher_catalog()

    if settings.COLLECT_SCHEDULER_ENABLED:
        await start_collect_scheduler(settings.COLLECT_SCHEDULER_TIMEZONE)
    else:
        logging.info("采集调度器未启用（COLLECT_SCHEDULER_ENABLED=false）")

    yield

    stop_collect_scheduler()
    await cancel_background()
    await close_db()


async def _migrate_sys_collect_tasks(conn) -> None:
    """sys_collect_tasks 启动期清理（补 plan_run_id 索引 + 清理僵尸 running）"""
    from sqlalchemy import text
    statements = [
        # 单进程部署：启动时仍为 running 的是上次进程异常退出遗留，不清理会让同类任务（含定时）永远被防重拦截
        "UPDATE sys_collect_tasks SET status = 'failed', finished_at = NOW(), "
        "message = COALESCE(message, '') || ' [服务重启，任务中断]' WHERE status = 'running'",
    ]
    for stmt in statements:
        try:
            await conn.execute(text(stmt))
        except Exception as e:
            logging.warning("sys_collect_tasks 迁移跳过: %s | %s", stmt, e)

    await _drop_unused_collect_task_details(conn)


async def _drop_unused_collect_task_details(conn) -> None:
    """删除废弃表 sys_collect_task_details（幂等）

    该表从未被任何代码读写（0 行 0 引用），单元级进度走 Redis + UnitTally 内存聚合。
    ORM 类已同步移除，残留表只会让新人误以为明细可查。
    """
    from sqlalchemy import text

    probe = await conn.execute(text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = 'sys_collect_task_details'"
    ))
    if not probe.fetchone():
        return

    try:
        n = (await conn.execute(
            text("SELECT count(*) FROM sys_collect_task_details")
        )).scalar()
        if n:
            # 有数据说明有我不知道的写入路径，宁可保留也不丢数据
            logging.warning(
                "sys_collect_task_details 有 %d 行数据，跳过 DROP（请人工确认）", n,
            )
            return
        await conn.execute(text("DROP TABLE IF EXISTS sys_collect_task_details"))
        logging.info("已删除废弃表 sys_collect_task_details（0 行）")
    except Exception as e:
        logging.warning("sys_collect_task_details 删除跳过: %s", e)


async def _rebuild_collect_config_tables(conn) -> None:
    """重建采集配置三表（破坏性 · 一次性 · 幂等）

    ⚠️ 会真删数据。执行前提（已确认）：
      - collect_plans 23 行，其中 enabled=true 的 0 行，无任何有效配置
      - collect_groups  0 行
      - 用户已确认不需要备份

    幂等策略：用 information_schema 判断新结构是否已就位，已就位则直接返回。
    这样第二次启动不会把用户新建的方案再删一遍。

    ⚠️ 必须在 create_all 之前调用。
    """
    from sqlalchemy import text

    probe = await conn.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'collect_plans'"
    ))
    cols = {r[0] for r in probe.fetchall()}
    if not cols:
        # 表不存在（首次部署）→ 无需重建，交给 create_all
        return
    if {"name", "schedule_type"} <= cols and "task_type" not in cols:
        logging.info("collect_plans 已是新结构，跳过重建")
        return

    # collect_plan_items 有 FK 指向 collect_plans，先删子表
    for stmt in [
        "DROP TABLE IF EXISTS collect_plan_items",
        "DROP TABLE IF EXISTS collect_plans",
        "DROP TABLE IF EXISTS collect_groups",
    ]:
        await conn.execute(text(stmt))
    logging.warning("已删除旧 collect_plans / collect_groups 表，将按新结构重建")


async def _rename_group_run_id_to_plan_run_id(conn) -> None:
    """sys_collect_tasks.group_run_id → plan_run_id（列名 + 索引名）

    ⚠️ 改索引名是因为 ORM 的 index=True 会按新列名生成
       ix_sys_collect_tasks_plan_run_id，旧索引名残留会造成同列两个索引。

    列内数据保留（RENAME COLUMN 不动数据），历史任务的关联关系不丢。
    """
    from sqlalchemy import text

    probe = await conn.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'sys_collect_tasks'"
    ))
    cols = {r[0] for r in probe.fetchall()}

    if "plan_run_id" in cols:          # 已改名，幂等返回
        return
    if "group_run_id" not in cols:     # 从未有过该列（全新库，create_all 已建好）
        return

    for stmt in [
        "DROP INDEX IF EXISTS ix_sys_collect_tasks_group_run_id",
        "ALTER TABLE sys_collect_tasks RENAME COLUMN group_run_id TO plan_run_id",
        "CREATE INDEX IF NOT EXISTS ix_sys_collect_tasks_plan_run_id ON sys_collect_tasks (plan_run_id)",
    ]:
        try:
            await conn.execute(text(stmt))
        except Exception as e:
            logging.warning("plan_run_id 改名跳过: %s | %s", stmt, e)
    logging.info("sys_collect_tasks.group_run_id 已改名为 plan_run_id")


async def _sync_fetcher_catalog() -> None:
    """启动时用代码注册表对账 collect_fetchers 表

    - 代码有 / DB 无 → 自动 INSERT（补录）
    - DB 有 / 代码无 → 标 status='orphan'（**不删**，保留现场 + 避免 CASCADE 掉方案项）
    - 两边都有但元数据变了 → UPDATE + warning

    ⚠️ 必须在 setup_collect_task_registry / setup_realtime_registry 之后调用。
    """
    from infrastructure.adapter.realtime import get_realtime_registry
    from infrastructure.adapter.scheduler.collect import get_collect_task_registry
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

    rt = get_realtime_registry()
    for q in rt.all():
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
