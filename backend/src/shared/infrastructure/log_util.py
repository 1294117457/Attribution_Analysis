"""log_util — 通用操作日志工具（DB + Redis 自管理，调用方零注入）

定位：
    日志子系统的**唯一**底层入口。所有日志读写都收敛到这里：
    - 不需要 DI 工厂，不需要调用方组装 service 实例
    - 内部自己开 DB session（attribution 库）+ 直连全局 redis 单例
    - 调用方只管 `from shared.infrastructure.log_util import log_util` 然后调方法

★ 通用性（2026-10-26）：
    本工具不绑定「采集」语义 —— 字段名全部通用化：
        service_name / category / action / meta / trigger_*
    采集场景下 category=facet、action=kind、meta=原始入参；
    其它业务场景（调度、用户操作、审计）可直接复用同一套表与方法。

状态机：
    init ──(update_status)──> running ──(update)──> success / partial_fail / failed
      │                        │
      │                        └─ DB 侧停留在 init，实时态以 Redis 为准
      └─(update)────────────────> success / partial_fail / failed

    ★ 为什么 DB 里叫 init 而不是 running：
      采集过程中的高频进度写只落 Redis（避免 DB IO 过重），
      DB 的 status 在「创建时=init」到「终态=success/failed」之间不变。
      读路径（query）会把 Redis 实时态合并回 DB 结果，前端看到的仍是 running。

写入三方法（语义互斥，职责严格分离）：
    create()          建日志：写 DB(init) + 写 Redis(init)  → 返回 log_id
    update_status()   改状态：★ 只改 Redis，永不写终态（终态必须走 update）
    update_progress() 改进度：只写 Redis（best-effort，Redis 故障不中断采集）
    update()          终态：写 DB(终态) + 清理 Redis key

    ★ 为什么 update_status 不再自动转终态：
      「改状态」和「落终态」是两种写语义 —— 前者只碰 Redis（高频、廉价），
      后者要写 DB 并清 Redis（低频、昂贵）。早期版本让 update_status
      遇到终态就自动转调 update()，导致调用方无法从代码上区分
      「我只是改个状态」还是「我在落终态」，且 Redis 清理时机被隐式决定。
      现在终态只能显式调用 update()，三方法职责清晰、调用点可预期。

读取两方法（前端按 service meta 的 name 查询）：
    query()           查某 service 最近 N 条（DB + Redis 实时进度合并）
    query_one()       查单条

被谁调用：
    1. 采集 service（daily 等）→ create / update_status / update_progress / update
    2. CatalogService（manage 面）→ query / query_one
    3. main.py lifespan → recover_orphan_logs（进程重启后收拾卡住的日志）
"""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

# ★ 全局单例直连：无需 DI 注入
from shared.infrastructure.connection.db_factory import db_session_factory
from shared.infrastructure.connection.redis_client import redis as redis_client
from shared.infrastructure.persistence.repositories import CollectLogRepository

logger = logging.getLogger(__name__)

# Redis 实时进度 key 前缀
REDIS_KEY_PREFIX = "collect:log"
REDIS_TTL = 3600  # 1 小时

# 终态集合：DB status 属于这些值时，不再合并 Redis 实时进度
TERMINAL_STATUSES = frozenset({"success", "partial_fail", "failed", "skipped"})

# 非终态集合：DB status 属于这些值时，合并 Redis 实时进度
LIVE_STATUSES = frozenset({"init", "pending", "running"})


class LogUtil:
    """通用操作日志工具（静态方法集合，无状态）

    ★ 无状态：所有方法自带 session / redis，不持有任何实例字段，
      因此可以安全地在任意协程里直接调用。
    """

    # ═══════════════════════════════════════════════════════════════
    # 写入方向
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    async def create(
        service_name: str,
        category: str,
        action: str,
        meta: dict,
        trigger_source: str = "manual",
        trigger_user: str | None = None,
    ) -> str:
        """创建日志（init 状态）

        流程：
            1. 生成 log_id
            2. INSERT collect_logs（init）—— 独立短事务（attribution 库）
            3. HSET Redis init hash + EXPIRE 1h

        Args:
            service_name: 执行者标识（采集时为 ServiceMeta.name）
            category: 分组维度（采集时为 tech/capital/fundamental/news/sentiment）
            action: 动作类型（采集时为 incremental/full_refresh/realtime）
            meta: 动态上下文（采集时为前端原始入参）
            trigger_source: 触发来源（manual/script/schedule）
            trigger_user: 触发用户（可选）

        Returns:
            log_id（UUID 字符串）

        Raises:
            Exception: DB 写入失败时抛出（调用方应中止采集）
                —— 宁可「没采成」，也不要「采完没日志」的孤儿数据。
        """
        log_id = str(uuid.uuid4())

        # 1. 写 DB（attribution 库，独立短事务）
        async with _db_ctx() as session:
            await CollectLogRepository(session).create(
                id=log_id,
                service_name=service_name,
                category=category,
                action=action,
                trigger_source=trigger_source,
                trigger_user=trigger_user,
                meta=meta,
            )

        # 2. 写 Redis 初始态（失败不阻断 —— DB 已有记录，前端仍能查到）
        try:
            redis_key = _redis_key(service_name, log_id)
            await redis_client.hset(redis_key, mapping={
                "status": "init",
                "progress": 0,
                "saved_count": 0,
                "fail_count": 0,
                "total_count": 0,
                "updated_at": datetime.now().isoformat(),
            })
            await redis_client.expire(redis_key, REDIS_TTL)
        except Exception as e:
            logger.warning(
                "log_util.create: Redis 初始态写入失败（log_id=%s）: %r",
                log_id, e,
            )

        return log_id

    @staticmethod
    async def update_status(
        log_id: str,
        service_name: str,
        status: str,
    ) -> None:
        """修改日志状态（★ 只写 Redis，不落终态）

        Args:
            log_id: 日志 ID
            service_name: 服务名
            status: 新状态（init / running）

        ★ 只写 Redis —— 采集过程中的高频状态变更不应该给 DB 造成 IO 压力；
          DB 的 status 保持 init 直到终态。

        ★ 本方法**不接受终态**。落终态必须显式调用 update()：
          终态要写 DB + 清 Redis，是两件事，不该藏在「改状态」里。
          传终态进来会被忽略（记 warning），避免静默产生
          「Redis 显示 success 但 DB 还是 init」的错位状态。
        """
        if status in TERMINAL_STATUSES:
            logger.warning(
                "log_util.update_status: 终态 %s 被忽略，请改用 update()"
                "（log_id=%s）",
                status, log_id,
            )
            return

        now = datetime.now().isoformat()
        try:
            redis_key = _redis_key(service_name, log_id)
            await redis_client.hset(
                redis_key, mapping={"status": status, "updated_at": now},
            )
            if status == "running":
                # ★ hsetnx：只在首次进入 running 时写 started_at，
                #   后续状态更新不能把开始时间冲掉
                await redis_client.hsetnx(redis_key, "started_at", now)
            await redis_client.expire(redis_key, REDIS_TTL)
        except Exception as e:
            logger.warning(
                "log_util.update_status: Redis 更新失败（log_id=%s）: %r",
                log_id, e,
            )

    @staticmethod
    async def update_progress(
        log_id: str,
        service_name: str,
        progress: int | None = None,
        saved_count: int | None = None,
        fail_count: int | None = None,
        total_count: int | None = None,
    ) -> None:
        """修改采集进度（只写 Redis）

        采集过程中的高频进度写全部走这里 —— 只碰 Redis，避免 DB IO 过重。

        Args:
            log_id: 日志 ID
            service_name: 服务名
            progress: 进度 0-100
            saved_count: 已入库记录数
            fail_count: 失败记录数
            total_count: 预估总量

        ★ best-effort：Redis 抖动不应该让整批采集失败，
          异常只记 warning，不向上抛。
        """
        mapping: dict[str, Any] = {}

        if progress is not None:
            mapping["progress"] = min(progress, 100)
        if saved_count is not None:
            mapping["saved_count"] = saved_count
        if fail_count is not None:
            mapping["fail_count"] = fail_count
        if total_count is not None:
            mapping["total_count"] = total_count

        if not mapping:
            return

        mapping["updated_at"] = datetime.now().isoformat()

        try:
            redis_key = _redis_key(service_name, log_id)
            await redis_client.hset(redis_key, mapping=mapping)
            await redis_client.expire(redis_key, REDIS_TTL)
        except Exception as e:
            logger.warning(
                "log_util.update_progress: Redis 更新失败（log_id=%s）: %r",
                log_id, e,
            )

    @staticmethod
    async def update(
        log_id: str,
        service_name: str,
        status: str,
        progress: int = 100,
        saved_count: int = 0,
        fail_count: int = 0,
        error: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """终态写入：写 DB + 清理 Redis

        流程：
            1. UPDATE collect_logs（终态 + 计数 + progress）—— 独立短事务
            2. DEL Redis key

        Args:
            log_id: 日志 ID
            service_name: 服务名
            status: 终态（success / partial_fail / failed）
            progress: 最终进度（failed 时应传实际进度，不是 100）
            saved_count: 已入库记录数
            fail_count: 失败记录数
            error: 错误信息（可选）
            duration_ms: 耗时毫秒（可选，不传则由 started_at 推算）

        ★ 顺序很重要：先写 DB 再删 Redis。
          反过来的话，中途那一次前端轮询会读到「DB 还是 init + Redis 已删」
          → 进度闪回 0。

        ★ 本方法不抛异常：终态写失败不该让采集任务崩掉，
          异常只记 error（此时 Redis key 保留，前端仍能看到最后的实时态）。
        """
        try:
            async with _db_ctx() as session:
                await CollectLogRepository(session).update(
                    log_id, status, saved_count, fail_count,
                    progress=progress, error=error,
                    finished_at=datetime.now(),
                    duration_ms=duration_ms,
                )
        except Exception as e:
            logger.error(
                "log_util.update: DB 终态写入失败（log_id=%s, status=%s）: %r",
                log_id, status, e,
            )

        # 清理 Redis（终态以 DB 为准，缓存留着只会误导）
        try:
            await redis_client.delete(_redis_key(service_name, log_id))
        except Exception as e:
            logger.warning(
                "log_util.update: Redis 清理失败（log_id=%s）: %r", log_id, e,
            )

    # ═══════════════════════════════════════════════════════════════
    # 读取方向
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    async def query(service_name: str, limit: int = 10) -> list[dict[str, Any]]:
        """查询某 service 最近 limit 条日志（DB + Redis 实时进度合并）

        Args:
            service_name: 服务名（与 ServiceMeta.name 一致）
            limit: 返回条数
        """
        async with _db_ctx() as session:
            logs = await CollectLogRepository(session).list_recent(
                service_name, limit=limit,
            )
        for log in logs:
            await LogUtil._merge_redis_progress(service_name, log)
        return logs

    @staticmethod
    async def query_one(
        log_id: str,
        service_name: str,
    ) -> dict[str, Any] | None:
        """查询单条日志（DB + Redis 实时进度合并）

        Args:
            log_id: 日志 ID
            service_name: 服务名
        """
        async with _db_ctx() as session:
            log = await CollectLogRepository(session).get_by_id(log_id)
        if log is None:
            return None
        await LogUtil._merge_redis_progress(service_name, log)
        return log

    # ═══════════════════════════════════════════════════════════════
    # 运维辅助
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    async def recover_orphan_logs(timeout_minutes: int = 30) -> int:
        """进程启动时恢复 orphan 日志

        扫描 collect_logs 中「已开始但未结束」的记录（status=init，
        即创建后进程就崩了，asyncio.Task 已死），全部标记为 failed。

        在 App lifespan startup 时调用 —— Redis 1h TTL 已过、
        asyncio 任务已死，这些日志永远不会结束，必须由启动器兜底。

        Args:
            timeout_minutes: orphan 判定阈值（默认 30 分钟）

        Returns:
            恢复的日志数量
        """
        from datetime import timedelta
        from sqlalchemy import select

        from shared.infrastructure.persistence.models import CollectLogDB

        cutoff = datetime.now() - timedelta(minutes=timeout_minutes)

        async with _db_ctx() as session:
            repo = CollectLogRepository(session)

            stmt = (
                select(CollectLogDB)
                .where(CollectLogDB.status == "init")
                .where(CollectLogDB.updated_at < cutoff)
            )
            orphans = (await session.execute(stmt)).scalars().all()

            if not orphans:
                return 0

            for log in orphans:
                await repo.update(
                    log.id,
                    "failed",
                    saved_count=log.saved_count or 0,
                    fail_count=log.fail_count or 0,
                    progress=log.progress or 0,
                    error=(
                        "process_restart: orphan recovered at "
                        f"{datetime.now().isoformat()}"
                    ),
                    finished_at=datetime.now(),
                )
                logger.warning(
                    "恢复 orphan 日志: log_id=%s, service=%s, started_at=%s",
                    log.id, log.service_name, log.started_at,
                )

            return len(orphans)

    # ═══════════════════════════════════════════════════════════════
    # 内部方法
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    async def _merge_redis_progress(
        service_name: str,
        log: dict[str, Any],
    ) -> None:
        """DB 数据 + Redis 实时进度合并（仅非终态才合并）"""
        if log.get("status") not in LIVE_STATUSES:
            return

        try:
            data = await redis_client.hgetall(
                _redis_key(service_name, log["id"])
            )
        except Exception as e:
            logger.warning("log_util 读取 Redis 进度失败: %r", e)
            return

        if not data:
            return

        for src, dst in [
            ("status", "status"),
            ("progress", "progress"),
            ("saved_count", "saved_count"),
            ("fail_count", "fail_count"),
            ("total_count", "total_count"),
            ("error", "error_message"),
        ]:
            if src in data:
                if dst in ("progress", "saved_count", "fail_count", "total_count"):
                    try:
                        log[dst] = int(data[src])
                    except (TypeError, ValueError):
                        pass
                else:
                    log[dst] = data[src]


# ═══════════════════════════════════════════════════════════════════════
# 模块级内部工具
# ═══════════════════════════════════════════════════════════════════════


@asynccontextmanager
async def _db_ctx() -> AsyncIterator[AsyncSession]:
    """采集日志库的独立短事务（attribution_db）

    每个写方法用完即抛，天然保证：
        - 日志写入与采集数据写入不共享事务
        - 上游事务 abort 不会污染日志写入
    """
    async with db_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def _redis_key(service_name: str, log_id: str) -> str:
    """Redis 实时进度 key"""
    return f"{REDIS_KEY_PREFIX}:{service_name}:{log_id}"


# 模块级单例（方法全是 staticmethod，单例仅为调用手感统一）
log_util = LogUtil()


__all__ = [
    "LogUtil",
    "log_util",
    "REDIS_KEY_PREFIX",
    "REDIS_TTL",
    "TERMINAL_STATUSES",
    "LIVE_STATUSES",
]
