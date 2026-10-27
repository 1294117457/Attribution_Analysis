"""CollectLogRepository — 通用操作日志仓储（表 collect_logs @ attribution_db）

提供 collect_logs 表的增删改查操作。

迁移说明（2026-10-26）：
    - 本文件从 `contexts/collect/infrastructure/persistence/repositories/collect_log_repository.py`
      迁到 `shared/infrastructure/persistence/repositories/`。
      原因同 models/collect_log.py —— collect_logs 是跨 context 的公共元数据表，
      配套 log_util 位于 shared/infrastructure/，避免 shared → contexts 反向依赖。
    - 字段改名 facet→category / kind→action / params→meta（通用化）。

事务约定：
    ★ 每个写方法内部自己 commit —— 日志写入与采集数据写入本来就不在同一事务里
      （attribution_db vs raw_data_db 物理隔离），自管 commit 可让调用方
      「用完即抛」，不残留未提交事务。
    ★ session 由调用方传入（与 shared 下其它仓储一致），本 repo 不开 session。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.infrastructure.persistence.models.collect_log import CollectLogDB


class CollectLogRepository:
    """通用操作日志仓储"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        id: str,
        service_name: str,
        category: str,
        action: str,
        trigger_source: str,
        meta: dict,
        trigger_user: str | None = None,
    ) -> None:
        """创建日志（init 状态）

        Args:
            id: UUID log_id，由 log_util 生成
            service_name: 执行者标识（采集时为 service 名）
            category: 分组维度（采集时是 tech/capital/fundamental/news/sentiment）
            action: 动作类型（采集时是 incremental/full_refresh/realtime）
            trigger_source: 触发来源（manual/script/schedule）
            meta: 动态上下文 JSONB（采集时存原始入参）
            trigger_user: 触发用户（可选）
        """
        stmt = insert(CollectLogDB).values(
            id=id,
            service_name=service_name,
            category=category,
            action=action,
            trigger_source=trigger_source,
            trigger_user=trigger_user,
            meta=meta,
            status="init",
            started_at=datetime.now(),
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def update(
        self,
        log_id: str,
        status: str,
        saved_count: int,
        fail_count: int,
        progress: int = 100,
        error: str | None = None,
        finished_at: datetime | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """终态写入

        Args:
            log_id: 日志 ID
            status: 终态（success/partial_fail/failed）
            saved_count: 已入库记录数
            fail_count: 失败记录数
            progress: 进度（默认 100）
            error: 错误信息（可选）
            finished_at: 完成时间（可选，默认当前时间）
            duration_ms: 耗时毫秒（可选）
        """
        stmt = (
            update(CollectLogDB)
            .where(CollectLogDB.id == log_id)
            .values(
                status=status,
                saved_count=saved_count,
                fail_count=fail_count,
                progress=progress,
                error_message=error,
                finished_at=finished_at or datetime.now(),
                duration_ms=duration_ms,
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def list_recent(
        self, service_name: str, limit: int = 10,
    ) -> list[dict[str, Any]]:
        """查询最近 N 条日志

        Args:
            service_name: 服务名
            limit: 返回条数

        Returns:
            日志列表（按 started_at 降序）
        """
        stmt = (
            select(CollectLogDB)
            .where(CollectLogDB.service_name == service_name)
            .order_by(CollectLogDB.started_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [_to_dict(r) for r in rows]

    async def get_by_id(self, log_id: str) -> dict[str, Any] | None:
        """按 ID 查单条

        Args:
            log_id: 日志 ID

        Returns:
            日志详情 dict 或 None
        """
        stmt = select(CollectLogDB).where(CollectLogDB.id == log_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _to_dict(row) if row else None


def _to_dict(row: CollectLogDB) -> dict[str, Any]:
    """ORM row → dict"""
    return {
        "id": str(row.id),
        "service_name": row.service_name,
        "category": row.category,
        "action": row.action,
        "trigger_source": row.trigger_source,
        "trigger_user": row.trigger_user,
        "meta": row.meta or {},
        "status": row.status,
        "total_count": row.total_count or 0,
        "saved_count": row.saved_count or 0,
        "fail_count": row.fail_count or 0,
        "progress": row.progress or 0,
        "duration_ms": row.duration_ms,
        "error_message": row.error_message,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


__all__ = ["CollectLogRepository"]
