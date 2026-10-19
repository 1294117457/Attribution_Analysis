"""StockConceptRepository Protocol

fetcher 返回 list[dict]，需通过 concept_id_map 解析
"""
from __future__ import annotations

from typing import Protocol


class StockConceptRepository(Protocol):
    """股票所属概念仓储协议"""

    async def upsert_by_concept_map(
        self,
        rows: list[dict],
        concept_id_map: dict[str, int],
    ) -> int: ...


__all__ = ["StockConceptRepository"]
