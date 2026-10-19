"""CollectLogService — 采集日志业务编排

Phase 2 重构（2026-10-19）：
    - 日志子系统独立闭环（route / service / persistence）
    - 无 AOP 装饰器，所有日志操作在此手动调用
    - 写方向：create_pending / mark_running / update_progress / mark_finished / mark_failed
    - 读方向：list_logs / get_log

被谁调用：
    1. log_handler.py  → list_logs / get_log
    2. 采集接口 service collect() → create_pending + mark_failed（dispatch 失败时回滚）
    3. TaskRunner._run() → mark_running / update_progress / mark_finished / mark_failed
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from contexts.collect.infrastructure.persistence.repositories import (
    CollectLogRepository,
)

logger = logging.getLogger(__name__)

# Redis 实时进度 key 前缀
REDIS_KEY_PREFIX = "collect:log"
REDIS_TTL = 3600  # 1 小时


class CollectLogService:
    """采集日志业务服务（日志子系统唯一业务入口）"""

    def __init__(
        self,
        session: AsyncSession,
        redis_client,  # aioredis.Redis
    ) -> None:
        self._session = session
        self._redis = redis_client
        self._repo = CollectLogRepository(session)

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
            2. INSERT collect_logs（pending）
            3. HSET Redis pending hash
            4. EXPIRE Redis 1h

        Returns:
            log_id（UUID 字符串）
        """
        log_id = str(uuid.uuid4())

        # 1. 写 DB
        await self._repo.create(
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
        await self._repo.update_status(log_id, "running", started_at=started_at)

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
        await self._repo.finish(
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

        Args:
            service_name: 服务名
            log_id: 日志 ID
            error: 错误信息
            saved_count: 已入库记录数
            fail_count: 失败记录数
        """
        finished_at = datetime.now()
        await self._repo.finish(
            log_id, "failed", saved_count, fail_count,
            error=error[:500], finished_at=finished_at,
        )

        redis_key = self._redis_key(service_name, log_id)
        await self._redis.hset(redis_key, mapping={
            "status": "failed",
            "error": error[:500],
            "updated_at": finished_at.isoformat(),
        })

    # ═══════════════════════════════════════════════════════════════
    # 读取方向
    # ═══════════════════════════════════════════════════════════════

    async def list_logs(
        self,
        service_name: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """查询最近 limit 条日志（合并 Redis 实时进度）"""
        logs = await self._repo.list_recent(service_name, limit=limit)
        for log in logs:
            await self._merge_redis_progress(service_name, log)
        return logs

    async def get_log(
        self,
        service_name: str,
        log_id: str,
    ) -> dict[str, Any] | None:
        """查询单条日志（合并 Redis 实时进度）"""
        log = await self._repo.get_by_id(log_id)
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
