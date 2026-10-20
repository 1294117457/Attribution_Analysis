"""CollectLogService — 采集日志业务编排

Phase 2 重构（2026-10-19）：
    - 日志子系统独立闭环（route / service / persistence）
    - 无 AOP 装饰器，所有日志操作在此手动调用
    - 写方向：create_pending / mark_running / update_progress / mark_finished / mark_failed
    - 读方向：list_logs / get_log

Step 8 修正（2026-10-20）—— session 自管理：
    - 移除 __init__ 的 session 参数，改为每次 DB 操作内部开独立短事务
    - collect_logs 表继承 AttribBase → 物理库是 attribution_db
    - 采集数据在 raw_data_db，两者物理隔离，天然不可能同事务
    - 因此日志写入与数据写入各自独立 commit，TaskRunner 无需持有任何 session

Step 9 重构（2026-10-20）—— Redis 全局单例直连：
    - 移除 __init__ 的 redis_client 参数
    - 服务内部直接 import 全局 redis 单例（无需 Depends 注入）
    - DI 工厂也不再传 log_service 时的 redis 依赖

为什么可以自管 session：
    CollectLogRepository 的每个写方法（create / update_status / finish）内部都自己 commit，
    日志写入与采集数据写入本来就不在同一事务里。
    自管 session 还额外消除了「复用被污染 session」的问题——
    即使上游数据写入失败导致事务 abort，mark_failed 用的也是全新的干净 session。

为什么 Redis 走全局单例：
    Redis 连接天然适合单例（连接池复用 + 进程级一致）。
    aioredis.from_url() 是纯构造函数，无 I/O，无须 lazy init / Lock。
    服务直接 import 即用，DI 层不再透传。

被谁调用：
    1. log_handler.py  → list_logs / get_log
    2. 采集接口 service collect() → create_pending + mark_failed（dispatch 失败时回滚）
    3. TaskRunner._run() → mark_running / update_progress / mark_finished / mark_failed
    4. main.py lifespan startup → recover_orphan_logs
"""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncIterator

from shared.infrastructure.connection.db_factory import db_session_factory
# ★ 全局单例直连：无需 DI 注入
from shared.infrastructure.connection.redis_client import redis as redis_client
from contexts.collect.infrastructure.persistence.repositories import (
    CollectLogRepository,
)

logger = logging.getLogger(__name__)

# Redis 实时进度 key 前缀
REDIS_KEY_PREFIX = "collect:log"
REDIS_TTL = 3600  # 1 小时


class CollectLogService:
    """采集日志业务服务（日志子系统唯一业务入口）

    ★ 不持有 session —— 每次 DB 操作自开一个独立的 attribution 库短事务。
    ★ 不持有 redis_client —— 直接用模块级单例 redis_client。
    """

    def __init__(self) -> None:
        self._redis = redis_client

    @asynccontextmanager
    async def _ctx(self) -> AsyncIterator[Any]:
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

    # ═══════════════════════════════════════════════════════════════
    # 写入方向
    # ═══════════════════════════════════════════════════════════════

    async def create_pending(
        self,
        service_name: str,
        facet: str,
        kind: str,
        params: dict,
        trigger_source: str = "manual",
        trigger_user: str | None = None,
    ) -> str:
        """创建采集日志（pending 状态）

        流程：
            1. 生成 log_id
            2. INSERT collect_logs（pending）—— 独立短事务
            3. HSET Redis pending hash
            4. EXPIRE Redis 1h

        Returns:
            log_id（UUID 字符串）
        """
        log_id = str(uuid.uuid4())

        # 1. 写 DB（attribution 库，独立事务）
        async with self._ctx() as session:
            await CollectLogRepository(session).create(
                id=log_id,
                service_name=service_name,
                facet=facet,
                kind=kind,
                trigger_source=trigger_source,
                trigger_user=trigger_user,
                params=params,
            )

        # 2. 写 Redis pending
        redis_key = self._redis_key(service_name, log_id)
        await self._redis.hset(redis_key, mapping={
            "status": "pending",
            "progress": 0,
            "saved_count": 0,
            "fail_count": 0,
            "total_count": 0,
            "updated_at": datetime.now().isoformat(),
        })
        await self._redis.expire(redis_key, REDIS_TTL)

        return log_id

    async def mark_running(self, service_name: str, log_id: str) -> None:
        """状态：pending → running

        Args:
            service_name: 服务名
            log_id: 日志 ID
        """
        started_at = datetime.now()
        async with self._ctx() as session:
            await CollectLogRepository(session).update_status(
                log_id, "running", started_at=started_at,
            )

        redis_key = self._redis_key(service_name, log_id)
        await self._redis.hset(redis_key, mapping={
            "status": "running",
            "started_at": started_at.isoformat(),
            "updated_at": started_at.isoformat(),
        })

    async def update_progress(
        self,
        service_name: str,
        log_id: str,
        progress: int,
        saved_count: int,
        fail_count: int,
        total_count: int,
    ) -> None:
        """实时进度：只写 Redis（不写 DB，避免 IO 太重）

        Args:
            service_name: 服务名
            log_id: 日志 ID
            progress: 0-100
            saved_count: 已入库记录数
            fail_count: 失败记录数
            total_count: 预估总量
        """
        redis_key = self._redis_key(service_name, log_id)
        await self._redis.hset(redis_key, mapping={
            "progress": min(progress, 100),
            "saved_count": saved_count,
            "fail_count": fail_count,
            "total_count": total_count,
            "updated_at": datetime.now().isoformat(),
        })

    async def mark_finished(
        self,
        service_name: str,
        log_id: str,
        status: str,  # "success" | "partial_fail"
        saved_count: int,
        fail_count: int,
    ) -> None:
        """终态：success / partial_fail

        写 DB 终态 + Redis 终态

        Args:
            service_name: 服务名
            log_id: 日志 ID
            status: "success" | "partial_fail"
            saved_count: 已入库记录数
            fail_count: 失败记录数
        """
        finished_at = datetime.now()
        async with self._ctx() as session:
            await CollectLogRepository(session).finish(
                log_id, status, saved_count, fail_count,
                progress=100, finished_at=finished_at,
            )

        redis_key = self._redis_key(service_name, log_id)
        await self._redis.hset(redis_key, mapping={
            "status": status,
            "progress": 100,
            "saved_count": saved_count,
            "fail_count": fail_count,
            "updated_at": finished_at.isoformat(),
        })

    async def mark_failed(
        self,
        service_name: str,
        log_id: str,
        error: str,
        saved_count: int = 0,
        fail_count: int = 0,
    ) -> None:
        """异常：failed（用于派发失败 / 采集异常）

        写 DB failed + Redis failed

        ★ 本方法用全新的独立 session —— 即使采集事务已 abort 也不受影响。

        Args:
            service_name: 服务名
            log_id: 日志 ID
            error: 错误信息
            saved_count: 已入库记录数
            fail_count: 失败记录数
        """
        finished_at = datetime.now()
        async with self._ctx() as session:
            await CollectLogRepository(session).finish(
                log_id, "failed", saved_count, fail_count,
                error=error[:500], finished_at=finished_at,
            )

        redis_key = self._redis_key(service_name, log_id)
        await self._redis.hset(redis_key, mapping={
            "status": "failed",
            "error": error[:500],
            "updated_at": finished_at.isoformat(),
        })

    async def recover_orphan_logs(self, timeout_minutes: int = 30) -> int:
        """进程启动时恢复 orphan 日志

        扫描 collect_logs 表中 status=running 且 updated_at 早于 timeout 分钟的记录，
        全部标记为 failed（原因：进程重启，asyncio.Task 已死，但日志卡在 running）。

        在 App lifespan startup 时调用 —— Redis 1h TTL 已过、asyncio 任务已死，
        这些日志永远不会结束，必须由启动器兜底。

        ★ 整个流程共用一个事务（select + 批量 finish 是同一次恢复操作）。

        Args:
            timeout_minutes: orphan 判定阈值（默认 30 分钟）

        Returns:
            恢复的日志数量
        """
        from datetime import datetime as _dt, timedelta as _td
        from sqlalchemy import select
        from contexts.collect.infrastructure.persistence.models.collect_log import (
            CollectLogDB,
        )

        cutoff = _dt.now() - _td(minutes=timeout_minutes)

        async with self._ctx() as session:
            repo = CollectLogRepository(session)

            # 1. 查 orphan 日志
            stmt = (
                select(CollectLogDB)
                .where(CollectLogDB.status == "running")
                .where(CollectLogDB.updated_at < cutoff)
            )
            orphans = (await session.execute(stmt)).scalars().all()

            if not orphans:
                return 0

            # 2. 批量标记 failed
            for log in orphans:
                await repo.finish(
                    log.id,
                    "failed",
                    saved_count=log.saved_count or 0,
                    fail_count=log.fail_count or 0,
                    error=f"process_restart: orphan recovered at {_dt.now().isoformat()}",
                    finished_at=_dt.now(),
                )
                logger.warning(
                    "恢复 orphan 日志: log_id=%s, service=%s, started_at=%s, updated_at=%s",
                    log.id, log.service_name, log.started_at, log.updated_at,
                )

            return len(orphans)

    # ═══════════════════════════════════════════════════════════════
    # 读取方向
    # ═══════════════════════════════════════════════════════════════

    async def list_logs(
        self,
        service_name: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """查询最近 limit 条日志（合并 Redis 实时进度）"""
        async with self._ctx() as session:
            logs = await CollectLogRepository(session).list_recent(
                service_name, limit=limit,
            )
        for log in logs:
            await self._merge_redis_progress(service_name, log)
        return logs

    async def get_log(
        self,
        service_name: str,
        log_id: str,
    ) -> dict[str, Any] | None:
        """查询单条日志（合并 Redis 实时进度）"""
        async with self._ctx() as session:
            log = await CollectLogRepository(session).get_by_id(log_id)
        if log is None:
            return None
        await self._merge_redis_progress(service_name, log)
        return log

    # ═══════════════════════════════════════════════════════════════
    # 内部方法
    # ═══════════════════════════════════════════════════════════════

    async def _merge_redis_progress(
        self,
        service_name: str,
        log: dict[str, Any],
    ) -> None:
        """DB 数据 + Redis 实时进度合并（仅 pending/running 状态）"""
        if log.get("status") not in ("pending", "running"):
            return

        redis_key = self._redis_key(service_name, log["id"])
        data = await self._redis.hgetall(redis_key)
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
                    log[dst] = int(data[src])
                else:
                    log[dst] = data[src]

    @staticmethod
    def _redis_key(service_name: str, log_id: str) -> str:
        return f"{REDIS_KEY_PREFIX}:{service_name}:{log_id}"


__all__ = ["CollectLogService"]