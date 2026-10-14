"""概念入选理由采集任务（adata stock.info.get_concept_ths）

按已有 stock_concept_members 关系，按股票循环 fetch F10 入选理由。
仅更新已有关系的 reason 字段，不新增关系。

依赖：必须先跑 concept + concept_membership 两个任务建立关系。
"""
from __future__ import annotations

import logging

from application.collect.task import BaseCollectTask, UnitResult, UnitTally
from application.port.data.concept import StockConceptsPort

logger = logging.getLogger(__name__)


class ConceptReasonCollectTask(BaseCollectTask):
    name = "concept_reason"
    facet = "fundamental"
    sub_facet = "concept"
    label = "概念入选理由"
    description = "F10 入选理由更新（adata get_concept_ths），只更新已有关系"
    default_params = {"only_missing": True}

    async def list_units(self, params: dict) -> list[str]:
        if params.get("symbol"):
            return [str(params["symbol"]).zfill(6)]
        return await self.ctx.concepts.member_symbols(
            only_missing_reason=bool(params.get("only_missing"))
        )

    async def collect_one(self, unit: str, params: dict) -> UnitResult:
        concept_list = (await self.ctx.gateway.fetch(
            StockConceptsPort, {"symbol": unit},
        )).items
        if not concept_list:
            return UnitResult(success=True, detail=unit, skipped=True)
        updated = await self.ctx.concepts.update_reasons(unit, concept_list)
        return UnitResult(success=True, detail=unit, saved_count=updated)

    def summary_message(self, tally: UnitTally) -> str:
        return (
            f"完成: 股票 {tally.success}（无概念 {tally.skip}），失败 {tally.fail}；"
            f"更新 reason {tally.saved} 条"
        )


__all__ = ["ConceptReasonCollectTask"]
