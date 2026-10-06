"""概念入选理由采集任务（adata stock.info.get_concept_ths）

按已有 stock_concept_members 关系，按股票循环 fetch F10 入选理由。
仅更新已有关系的 reason 字段，不新增关系。

依赖：必须先跑 concept + concept_membership 两个任务建立关系。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from sqlalchemy import select

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
from infrastructure.persistence.models.concept import ConceptMemberDB

logger = logging.getLogger(__name__)

class ConceptReasonCollectTask(BaseCollectTask):
    name = "concept_reason"
    facet = "fundamental"
    sub_facet = "concept"
    label = "概念入选理由"
    description = "F10 入选理由更新（adata get_concept_ths），只更新已有关系"
    default_params = {"only_missing": True}

    async def list_units(self, params: dict) -> list[str]:
        # 单元 = symbol
        if params.get("symbol"):
            return [str(params["symbol"]).zfill(6)]
        async with AsyncSessionLocal() as session:
            rows = await session.execute(
                select(ConceptMemberDB.symbol).distinct()
            )
            symbols = sorted({r[0] for r in rows.all()})
        if params.get("only_missing"):
            # 只取 reason 缺失的 symbol
            async with AsyncSessionLocal() as session:
                rows = await session.execute(
                    select(ConceptMemberDB.symbol)
                    .where((ConceptMemberDB.reason.is_(None)) | (ConceptMemberDB.reason == ""))
                    .distinct()
                )
                symbols = sorted({r[0] for r in rows.all()})
        limit = params.get("limit")
        return symbols[: int(limit)] if limit else symbols

    async def collect_one(self, unit: str, params: dict) -> UnitResult:
        fetcher = get_registry().get(ConceptFetcher)
        # 调 fetcher 已有的方法
        concept_list = await self._fetch_with_limit(fetcher, unit)
        if not concept_list:
            return UnitResult(success=True, detail=unit, skipped=True)
        # 写回 reason：按 (symbol, index_code) 命中
        async with AsyncSessionLocal() as session:
            rows = await session.execute(
                select(ConceptMemberDB).where(ConceptMemberDB.symbol == unit)
            )
            members = list(rows.scalars().all())
            index_to_member = {m.concept_id: m for m in members}
            # 调 fetcher 返回的是 index_code，需要查 concept_id
            from infrastructure.persistence.models.concept import ConceptsDB
            index_codes = [b.index_code for b in concept_list if b.index_code]
            if not index_codes:
                return UnitResult(success=True, detail=unit, saved_count=0)
            concept_rows = await session.execute(
                select(ConceptsDB).where(ConceptsDB.index_code.in_(index_codes))
            )
            id_by_index = {c.index_code: c.id for c in concept_rows.scalars().all()}
            updated = 0
            for b in concept_list:
                cid = id_by_index.get(b.index_code)
                if cid is None or cid not in index_to_member:
                    continue
                m = index_to_member[cid]
                if b.reason and m.reason != b.reason:
                    m.reason = b.reason
                    updated += 1
            await session.commit()
        return UnitResult(success=True, detail=unit, saved_count=updated)

    def summary_message(self, tally: UnitTally) -> str:
        return (
            f"完成: 股票 {tally.success}（无概念 {tally.skip}），失败 {tally.fail}；"
            f"更新 reason {tally.saved} 条"
        )

    def _check_cancel(self) -> None:
        if is_cancelled(self._task_id):
            raise Cancelled()

    async def _fetch_with_limit(self, fetcher, symbol) -> list:
        """调 fetcher.fetch_concepts_by_stock"""
        try:
            return await asyncio.to_thread(fetcher.fetch_concepts_by_stock, symbol)
        except Exception as e:
            logger.warning("get_concept_ths %s 失败: %s", symbol, e)
            return []