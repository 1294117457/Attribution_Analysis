"""采集接口元数据 / 采集方案 / 采集方案项 仓储"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.collect_config import (
    CollectFetcherDB,
    CollectPlanDB,
    CollectPlanItemDB,
)


class CollectConfigRepoImpl:
    """只做读写，不 commit（由调用方控制事务）

    说明：session 由调用方（CollectManageService）在
    `async with self._session_factory() as session:` 块内注入，
    本仓储不持有 session，避免单例 repo 持有失效 session 的问题。
    """

    # ── 采集接口元数据 ──────────────────────────────────────────────────

    async def list_fetchers(self, session: AsyncSession) -> list[CollectFetcherDB]:
        return list((
            await session.execute(
                select(CollectFetcherDB).order_by(
                    CollectFetcherDB.kind,
                    CollectFetcherDB.sort_order,
                    CollectFetcherDB.task_type,
                )
            )
        ).scalars().all())

    async def get_fetcher(
        self, task_type: str, session: AsyncSession,
    ) -> Optional[CollectFetcherDB]:
        return await session.get(CollectFetcherDB, task_type)

    # ── 采集方案 ────────────────────────────────────────────────────────

    async def list_plans(self, session: AsyncSession) -> list[CollectPlanDB]:
        return list((
            await session.execute(select(CollectPlanDB).order_by(CollectPlanDB.id))
        ).scalars().all())

    async def get_plan(
        self, plan_id: int, session: AsyncSession,
    ) -> Optional[CollectPlanDB]:
        return await session.get(CollectPlanDB, plan_id)

    async def create_plan(self, session: AsyncSession, **fields) -> CollectPlanDB:
        plan = CollectPlanDB(**fields)
        session.add(plan)
        await session.flush()
        return plan

    async def update_plan(
        self, session: AsyncSession, plan: CollectPlanDB, **fields,
    ) -> CollectPlanDB:
        for k, v in fields.items():
            setattr(plan, k, v)
        await session.flush()
        return plan

    async def delete_plan(self, session: AsyncSession, plan: CollectPlanDB) -> None:
        """删除方案；方案项由 FK ondelete=CASCADE 自动清理"""
        await session.delete(plan)
        await session.flush()

    async def touch_plan(
        self, session: AsyncSession, plan_id: int, task_id: int,
    ) -> None:
        plan = await session.get(CollectPlanDB, plan_id)
        if plan is not None:
            plan.last_run_at = datetime.now()
            plan.last_task_id = task_id

    # ── 采集方案项 ──────────────────────────────────────────────────────

    async def list_plan_items(
        self, session: AsyncSession, plan_id: int,
    ) -> list[CollectPlanItemDB]:
        """按执行顺序返回方案的方案项（已过滤 enabled=False）"""
        return list((
            await session.execute(
                select(CollectPlanItemDB)
                .where(
                    CollectPlanItemDB.plan_id == plan_id,
                    CollectPlanItemDB.enabled.is_(True),
                )
                .order_by(CollectPlanItemDB.sort_order, CollectPlanItemDB.id)
            )
        ).scalars().all())

    async def list_all_plan_items(
        self, session: AsyncSession, plan_id: int,
    ) -> list[CollectPlanItemDB]:
        """返回方案的全部方案项（含 disabled），供 UI 回显"""
        return list((
            await session.execute(
                select(CollectPlanItemDB)
                .where(CollectPlanItemDB.plan_id == plan_id)
                .order_by(CollectPlanItemDB.sort_order, CollectPlanItemDB.id)
            )
        ).scalars().all())

    async def replace_plan_items(
        self, session: AsyncSession, plan_id: int, items: list[dict],
    ) -> None:
        """全量替换方案项（PUT 语义，差量更新）

        ⚠️ 不能简单 DELETE 全部再 INSERT —— 那样 sort_order 变化会导致
           方案项 id 全部变化。这里保留 id 不变的行，只删/增/改差异。
        """
        existing = {
            it.task_type: it
            for it in await self.list_all_plan_items(session, plan_id)
        }
        wanted = {it["task_type"] for it in items}

        for task_type, row in existing.items():
            if task_type not in wanted:
                await session.delete(row)

        for idx, it in enumerate(items):
            task_type = it["task_type"]
            sort_order = idx * 10          # 10 的倍数，便于中间插入
            row = existing.get(task_type)
            if row is not None:
                row.params = dict(it.get("params") or {})
                row.enabled = bool(it.get("enabled", True))
                row.sort_order = sort_order
            else:
                session.add(CollectPlanItemDB(
                    plan_id=plan_id,
                    task_type=task_type,
                    params=dict(it.get("params") or {}),
                    enabled=bool(it.get("enabled", True)),
                    sort_order=sort_order,
                ))
        await session.flush()


__all__ = ["CollectConfigRepoImpl"]
