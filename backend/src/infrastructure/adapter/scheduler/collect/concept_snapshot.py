"""概念行情快照采集任务（adata stock.market.get_market_concept_current_ths）

按活跃概念逐个拉当前行情快照，写入 concept_snapshots 表（追加式时序）。
依赖：必须先跑 concept 任务。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from infrastructure.adapter import get_registry
from application.port.collector_port import ConceptFetcher
from infrastructure.adapter.scheduler.collect.base import (
    BaseCollectTask,
    Cancelled,
    UnitResult,
    UnitTally,
    is_cancelled,
)
from infrastructure.persistence.connection import AsyncSessionLocal
from infrastructure.persistence.models.concept import ConceptSnapshotDB

logger = logging.getLogger(__name__)



class ConceptSnapshotCollectTask(BaseCollectTask):
    name = "concept_snapshot"
    facet = "fundamental"
    sub_facet = "concept"
    label = "概念行情快照"
    description = "每批采集每个概念写一行快照（adata get_market_concept_current_ths）"
    default_params = {}
    sort_order = 30

    async def list_units(self, params: dict) -> list[str]:
        # 单元 = index_code
        if params.get("index_code"):
            return [str(params["index_code"])]
        async with AsyncSessionLocal() as session:
            from infrastructure.persistence.models.concept import ConceptsDB
            rows = await session.execute(
                select(ConceptsDB.index_code)
                .where(ConceptsDB.is_active == True)  # noqa: E712
            )
            return sorted({r[0] for r in rows.all()})

    async def collect_one(self, unit: str, params: dict) -> UnitResult:
        fetcher = get_registry().get(ConceptFetcher)
        snap = await self._fetch_snapshot(fetcher, unit)
        if not snap:
            return UnitResult(success=True, detail=unit, skipped=True)
        async with AsyncSessionLocal() as session:
            # 查 concept_name
            from infrastructure.persistence.models.concept import ConceptsDB
            from sqlalchemy import select
            row = (await session.execute(
                select(ConceptsDB.name).where(ConceptsDB.index_code == unit)
            )).first()
            concept_name = row[0] if row else unit
            session.add(ConceptSnapshotDB(
                index_code=unit,
                concept_name=concept_name,
                trade_time=datetime.now(timezone.utc),
                open_price=snap.get("open"),
                high=snap.get("high"),
                low=snap.get("low"),
                price=snap.get("price"),
                prev_close=snap.get("prev_close"),
                pct_change=snap.get("change_pct"),
                source="ths",
                captured_at=datetime.now(timezone.utc),
            ))
            await session.commit()
        return UnitResult(success=True, detail=unit, saved_count=1)

    def summary_message(self, tally: UnitTally) -> str:
        return (
            f"完成: 概念 {tally.success}（无快照 {tally.skip}），失败 {tally.fail}；"
            f"写入 {tally.saved} 条"
        )

    def _check_cancel(self) -> None:
        if is_cancelled(self._task_id):
            raise Cancelled()

    async def _fetch_snapshot(self, fetcher, index_code) -> dict | None:
        """调 fetcher.fetch_current_snapshot（adata 扩展方法）"""
        try:
            return await asyncio.to_thread(fetcher.fetch_current_snapshot, index_code)
        except Exception as e:
            logger.warning("get_market_concept_current_ths %s 失败: %s", index_code, e)
            return None
