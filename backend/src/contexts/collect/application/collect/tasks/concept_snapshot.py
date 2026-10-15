"""概念行情快照采集任务（adata stock.market.get_market_concept_current_ths）

按活跃概念逐个拉当前行情快照，写入 concept_snapshots 表（追加式时序）。
依赖：必须先跑 concept 任务。
"""
from __future__ import annotations

import logging
from datetime import datetime

from contexts.collect.application.collect.task import BaseCollectTask, UnitResult, UnitTally
from contexts.data.application.port.concept import ConceptSnapshotPort
from contexts.market.domain.services.market_session import market_now

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
        if params.get("index_code"):
            return [str(params["index_code"])]
        return await self.ctx.concepts.active_index_codes()

    async def collect_one(self, unit: str, params: dict) -> UnitResult:
        items = (await self.ctx.gateway.fetch(
            ConceptSnapshotPort, {"index_code": unit},
        )).items
        if not items:
            return UnitResult(success=True, detail=unit, skipped=True)
        snap = items[0]
        await self.ctx.concepts.add_snapshot(unit, snap, market_now())
        return UnitResult(success=True, detail=unit, saved_count=1)

    def summary_message(self, tally: UnitTally) -> str:
        return (
            f"完成: 概念 {tally.success}（无快照 {tally.skip}），失败 {tally.fail}；"
            f"写入 {tally.saved} 条"
        )


__all__ = ["ConceptSnapshotCollectTask"]
