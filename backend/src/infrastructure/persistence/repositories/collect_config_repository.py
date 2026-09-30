"""采集方案 / 采集任务组仓储"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.collect_config import CollectGroupDB, CollectPlanDB


class CollectConfigRepoImpl:
    """只做读写，不 commit（由调用方控制事务）"""

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    # ── 采集方案 ──────────────────────────────────────────────────────

    async def list_plans(self) -> list[CollectPlanDB]:
        return list((await self._s.execute(select(CollectPlanDB))).scalars().all())

    async def get_plan(self, task_type: str) -> Optional[CollectPlanDB]:
        return (
            await self._s.execute(select(CollectPlanDB).where(CollectPlanDB.task_type == task_type))
        ).scalars().first()

    async def upsert_plan(self, task_type: str, **fields) -> CollectPlanDB:
        plan = await self.get_plan(task_type)
        if plan is None:
            plan = CollectPlanDB(task_type=task_type)
            self._s.add(plan)
        for k, v in fields.items():
            setattr(plan, k, v)
        await self._s.flush()
        return plan

    async def touch_plan(self, task_type: str, task_id: int) -> None:
        plan = await self.get_plan(task_type)
        if plan is not None:
            plan.last_run_at = datetime.now()
            plan.last_task_id = task_id

    # ── 采集任务组 ────────────────────────────────────────────────────

    async def list_groups(self) -> list[CollectGroupDB]:
        return list(
            (await self._s.execute(select(CollectGroupDB).order_by(CollectGroupDB.id))).scalars().all()
        )

    async def get_group(self, group_id: int) -> Optional[CollectGroupDB]:
        return await self._s.get(CollectGroupDB, group_id)

    async def create_group(self, **fields) -> CollectGroupDB:
        group = CollectGroupDB(**fields)
        self._s.add(group)
        await self._s.flush()
        return group

    async def delete_group(self, group: CollectGroupDB) -> None:
        await self._s.delete(group)
