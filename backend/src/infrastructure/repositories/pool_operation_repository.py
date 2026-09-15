"""池操作记录仓储实现"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from domain.stock_pool.repository import PoolOperationRepository
from infrastructure.database.models.pool import PoolOperationDB


class PoolOperationRepoImpl(PoolOperationRepository):
    """池操作记录仓储实现"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        pool_id: int,
        operation_type: str,
        params: dict,
    ) -> int:
        db = PoolOperationDB(
            pool_id=pool_id,
            operation_type=operation_type,
            status="pending",
            params=params,
            progress={"done": 0, "total": 0, "failed": 0},
            created_at=datetime.now(),
        )
        self._session.add(db)
        await self._session.flush()
        await self._session.refresh(db)
        return db.id

    async def find_by_id(self, op_id: int) -> Optional[dict]:
        stmt = select(PoolOperationDB).where(PoolOperationDB.id == op_id)
        result = await self._session.execute(stmt)
        db = result.scalar_one_or_none()
        return self._to_dict(db) if db else None

    async def list_by_pool(
        self,
        pool_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        stmt = (
            select(PoolOperationDB)
            .where(PoolOperationDB.pool_id == pool_id)
            .order_by(PoolOperationDB.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        dbs = result.scalars().all()
        return [self._to_dict(db) for db in dbs]

    async def update_status(
        self,
        op_id: int,
        status: str,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        values = {"status": status}
        if started_at:
            values["started_at"] = started_at
        if finished_at:
            values["finished_at"] = finished_at
        if error_message:
            values["error_message"] = error_message

        stmt = (
            update(PoolOperationDB)
            .where(PoolOperationDB.id == op_id)
            .values(**values)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def update_progress(
        self,
        op_id: int,
        done: int,
        total: int,
        failed: int = 0,
    ) -> bool:
        stmt = (
            update(PoolOperationDB)
            .where(PoolOperationDB.id == op_id)
            .values(
                progress={"done": done, "total": total, "failed": failed},
                status="running",
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def update_result(
        self, op_id: int, result_summary: dict
    ) -> bool:
        stmt = (
            update(PoolOperationDB)
            .where(PoolOperationDB.id == op_id)
            .values(
                result_summary=result_summary,
                finished_at=datetime.now(),
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    def _to_dict(self, db: PoolOperationDB) -> dict:
        return {
            "id": db.id,
            "pool_id": db.pool_id,
            "operation_type": db.operation_type,
            "status": db.status,
            "params": db.params,
            "result_summary": db.result_summary,
            "progress": db.progress,
            "error_message": db.error_message,
            "started_at": db.started_at,
            "finished_at": db.finished_at,
            "created_at": db.created_at,
        }
