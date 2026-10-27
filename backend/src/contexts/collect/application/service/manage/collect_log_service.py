"""CollectLogService — 采集日志业务编排（兼容层，2026-10-26 起废弃）

⚠️ **本类已废弃**，新代码请直接用 `shared.infrastructure.log_util`：

    from shared.infrastructure.log_util import log_util
    await log_util.create(...)
    await log_util.update_status(...)
    await log_util.update_progress(...)
    await log_util.update(...)
    await log_util.query(...)

为什么保留：
    - 其余 26 个 collect service 仍在用旧的 `create_pending / mark_running /
      update_progress / mark_finished / mark_failed` 方法名；
      这些 service 即将被清理，届时本文件可整体删除。
    - 本文件现在是**纯转发层**，所有真实逻辑都在 log_util 里，
      两套实现不会产生行为分叉。

方法名映射（旧 → 新）：
    create_pending    → log_util.create
    mark_running      → log_util.update_status(status="running")
    update_progress   → log_util.update_progress
    mark_finished     → log_util.update(status="success"/"partial_fail")
    mark_failed       → log_util.update(status="failed")
    list_logs         → log_util.query
    get_log           → log_util.query_one
    recover_orphan_logs → log_util.recover_orphan_logs
"""
from __future__ import annotations

import logging
from typing import Any

from shared.infrastructure.log_util import (
    REDIS_KEY_PREFIX,
    REDIS_TTL,
    log_util,
)

logger = logging.getLogger(__name__)


class CollectLogService:
    """采集日志业务服务（兼容层 → 转发到 log_util）

    ★ 无状态：所有方法转发给 log_util，不持有 session / redis。
    """

    # ── 写入方向 ──────────────────────────────────────────────

    async def create_pending(
        self,
        service_name: str,
        facet: str,
        kind: str,
        params: dict,
        trigger_source: str = "manual",
        trigger_user: str | None = None,
    ) -> str:
        """创建采集日志（init 状态）→ 返回 log_id

        ★ 旧签名保留 facet / kind / params（26 个 service 在用），
          内部转成 log_util 的通用字段 category / action / meta。
        """
        return await log_util.create(
            service_name=service_name,
            category=facet,
            action=kind,
            meta=params,
            trigger_source=trigger_source,
            trigger_user=trigger_user,
        )

    async def mark_running(self, service_name: str, log_id: str) -> None:
        """状态：init → running（只写 Redis）"""
        await log_util.update_status(
            log_id, service_name=service_name, status="running",
        )

    async def update_progress(
        self,
        service_name: str,
        log_id: str,
        progress: int,
        saved_count: int,
        fail_count: int,
        total_count: int,
    ) -> None:
        """实时进度：只写 Redis"""
        await log_util.update_progress(
            log_id,
            service_name=service_name,
            progress=progress,
            saved_count=saved_count,
            fail_count=fail_count,
            total_count=total_count,
        )

    async def mark_finished(
        self,
        service_name: str,
        log_id: str,
        status: str,
        saved_count: int,
        fail_count: int,
    ) -> None:
        """终态：success / partial_fail"""
        await log_util.update(
            log_id,
            service_name=service_name,
            status=status,
            progress=100,
            saved_count=saved_count,
            fail_count=fail_count,
        )

    async def mark_failed(
        self,
        service_name: str,
        log_id: str,
        error: str,
        saved_count: int = 0,
        fail_count: int = 0,
    ) -> None:
        """异常：failed"""
        await log_util.update(
            log_id,
            service_name=service_name,
            status="failed",
            progress=0,
            saved_count=saved_count,
            fail_count=fail_count,
            error=error,
        )

    # ── 读取方向 ──────────────────────────────────────────────

    async def list_logs(
        self, service_name: str, limit: int = 10,
    ) -> list[dict[str, Any]]:
        """查询最近 limit 条日志（DB + Redis 实时进度合并）"""
        return await log_util.query(service_name=service_name, limit=limit)

    async def get_log(
        self, service_name: str, log_id: str,
    ) -> dict[str, Any] | None:
        """查询单条日志（DB + Redis 实时进度合并）"""
        return await log_util.query_one(
            log_id=log_id, service_name=service_name,
        )

    # ── 运维辅助 ──────────────────────────────────────────────

    async def recover_orphan_logs(self, timeout_minutes: int = 30) -> int:
        """进程启动时恢复 orphan 日志"""
        return await log_util.recover_orphan_logs(
            timeout_minutes=timeout_minutes,
        )


__all__ = ["CollectLogService", "REDIS_KEY_PREFIX", "REDIS_TTL"]
