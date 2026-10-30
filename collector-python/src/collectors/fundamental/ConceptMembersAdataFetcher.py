"""ConceptMembersAdataFetcher：概念成分股（同花顺 adata concept_constituent_ths）—— step7 重构版"""
from __future__ import annotations

from pydantic import BaseModel

from collectors.base import BaseFetcher
from core.adata_client import get_adata_client
from collectors.fundamental.ConceptListAdataFetcher import (
    _rows, _symbol,
)


class ConceptMembersAdataFetcher(BaseFetcher):
    fetcher_type = "concept_members_adata"
    source = "adata"
    label = "概念成分股（同花顺 adata）"

    def __init__(self) -> None:
        self._c = get_adata_client()
        self._sdk = self._c.sdk

    async def fetch(self, **params) -> list[BaseModel]:
        index_code = params.get("index_code")
        if not index_code:
            raise ValueError("index_code 必填")
        index_code = str(index_code).strip()
        if index_code.endswith(".0"):
            index_code = index_code[:-2]

        # ★ ★ index_code 必须是**纯 6 位数字**（如 885996 / 885652）。
        #   带后缀（如 "885001.TI"）会让 adata 内部解析失败 →
        #   ValueError('substring not found') → 整个采集任务失败。
        #
        #   实测（同一时段 4 次连续调用，结果完全一致）：
        #     index_code=885996  → 87 条
        #     index_code=885652  → 15 条
        #     concept_code=308969 → 0 条   ← 网页代码反而不通
        #   → 主路径用 index_code；concept_code 仅作为上游明确支持时的备选。
        df = await self._c.call(
            lambda: self._sdk.stock.info.concept_constituent_ths(
                index_code=index_code),
            "concept_constituent_ths",
        )
        items: list[dict] = []
        seen: set[str] = set()
        for row in _rows(df):
            sym = _symbol(row.get("stock_code"))
            if sym and sym not in seen:
                seen.add(sym)
                items.append({"index_code": index_code, "symbol": sym})
        return items


__all__ = ["ConceptMembersAdataFetcher"]
