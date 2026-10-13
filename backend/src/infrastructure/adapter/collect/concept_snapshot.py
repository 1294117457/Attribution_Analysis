"""概念行情快照采集任务（adata stock.market.get_market_concept_current_ths）

按活跃概念逐个拉当前行情快照，写入 concept_snapshots 表（追加式时序）。
依赖：必须先跑 concept 任务。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from application.port.data.concept import ConceptSnapshotPort
from domain.service.market_session import market_now
from infrastructure.adapter.data import get_data_gateway
from infrastructure.adapter.collect.base import (
    BaseCollectTask,
    UnitResult,
    UnitTally,
)
from infrastructure.persistence.connection import AsyncSessionLocal
from infrastructure.persistence.models.concept import ConceptsDB, ConceptSnapshotDB

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
            rows = await session.execute(
                select(ConceptsDB.index_code)
                .where(ConceptsDB.is_active == True)  # noqa: E712
            )
            return sorted({r[0] for r in rows.all()})

    async def collect_one(self, unit: str, params: dict) -> UnitResult:
        items = (await get_data_gateway().fetch(ConceptSnapshotPort, {"index_code": unit})).items
        if not items:
            return UnitResult(success=True, detail=unit, skipped=True)
        snap = items[0]
        async with AsyncSessionLocal() as session:
            row = (await session.execute(
                select(ConceptsDB.name).where(ConceptsDB.index_code == unit)
            )).first()
            concept_name = row[0] if row else unit
            now = datetime.now(timezone.utc)
            session.add(ConceptSnapshotDB(
                index_code=unit,
                concept_name=concept_name,
                # trade_time 列为 TIMESTAMP WITHOUT TIME ZONE，存市场本地时间
                trade_time=market_now().replace(tzinfo=None),
                open_price=snap.open,
                high=snap.high,
                low=snap.low,
                price=snap.price,
                prev_close=snap.prev_close,
                pct_change=snap.change_pct,
                source="ths",
                captured_at=now,
            ))
            await session.commit()
        return UnitResult(success=True, detail=unit, saved_count=1)

    def summary_message(self, tally: UnitTally) -> str:
        return (
            f"完成: 概念 {tally.success}（无快照 {tally.skip}），失败 {tally.fail}；"
            f"写入 {tally.saved} 条"
        )
