"""CollectLogRepository — 采集日志仓储

提供 collect_logs 表的增删改查操作。
设计说明：
    - create(): 创建日志（pending 状态），handler 同步调用
    - update_status(): 更新状态（pending → running）
    - finish(): 终态写入（success/partial_fail/failed）
    - list_recent(): 查询最近 N 条日志
    - get_by_id(): 按 ID 查单条

参考文档：docs/backend-docs/dev/level2/step1采集模块优化/06采集日志进度优化/01-采集日志进度优化方案.md §八
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.collect.infrastructure.persistence.models.collect_log import CollectLogDB


class CollectLogRepository:
    """采集日志仓储"""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def create(
        self,
        id: str,
        service_name: str,
        facet: str,
        kind: str,
        trigger_source: str,
        params: dict,
        trigger_user: str | None = None,
    ) -> None:
        """创建日志（pending 状态）
        
        Args:
            id: UUID log_id，handler 同步生成
            service_name: 服务名（与 ServiceMeta.name 一致）
            facet: 大类（tech/capital/fundamental/news/sentiment）
            kind: 采集类型（incremental/full_refresh/realtime）
            trigger_source: 触发来源（manual/script/schedule）
            params: 前端原始入参
            trigger_user: 触发用户（可选）
        """
        stmt = insert(CollectLogDB).values(
            id=id,
            service_name=service_name,
            facet=facet,
            kind=kind,
            trigger_source=trigger_source,
            trigger_user=trigger_user,
            params=params,
            status="pending",
            started_at=datetime.now(),
        )
        await self._session.execute(stmt)
        await self._session.commit()
    
    async def update_status(
        self,
        log_id: str,
        status: str,
        started_at: datetime | None = None,
    ) -> None:
        """更新状态（pending → running）
        
        Args:
            log_id: 日志 ID
            status: 新状态
            started_at: 开始时间（可选）
        """
        values = {"status": status}
        if started_at:
            values["started_at"] = started_at
        stmt = (
            update(CollectLogDB)
            .where(CollectLogDB.id == log_id)
            .values(**values)
        )
        await self._session.execute(stmt)
        await self._session.commit()
    
    async def finish(
        self,
        log_id: str,
        status: str,
        saved_count: int,
        fail_count: int,
        progress: int = 100,
        error: str | None = None,
        finished_at: datetime | None = None,
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
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()
    
    async def list_recent(self, service_name: str, limit: int = 10) -> list[dict[str, Any]]:
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
        "facet": row.facet,
        "kind": row.kind,
        "trigger_source": row.trigger_source,
        "trigger_user": row.trigger_user,
        "params": row.params or {},
        "status": row.status,
        "total_count": row.total_count or 0,
        "saved_count": row.saved_count or 0,
        "fail_count": row.fail_count or 0,
        "progress": row.progress or 0,
        "error_message": row.error_message,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


__all__ = ["CollectLogRepository"]
