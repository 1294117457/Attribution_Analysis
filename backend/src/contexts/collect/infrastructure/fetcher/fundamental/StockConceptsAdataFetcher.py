"""StockConceptsAdataFetcher：股票所属概念（同花顺 adata get_concept_ths）—— step7 重构版"""
from __future__ import annotations

from pydantic import BaseModel

from contexts.collect.infrastructure.fetcher.base import BaseFetcher
from contexts.collect.infrastructure.connect.adata_client import get_adata_client
from contexts.collect.infrastructure.fetcher.fundamental.ConceptListAdataFetcher import (
    _code, _rows, _str,
)


class StockConceptsAdataFetcher(BaseFetcher):
    fetcher_type = "stock_concepts_adata"
    source = "adata"
    label = "股票所属概念（同花顺 adata）"

    def __init__(self) -> None:
        self._c = get_adata_client()
        self._sdk = self._c.sdk

    async def fetch(self, **params) -> list[BaseModel]:
        symbol = params.get("symbol")
        if not symbol:
            raise ValueError("symbol 必填")

        def call():
            try:
                return self._sdk.stock.info.get_concept_ths(stock_code=symbol)
            except AttributeError:
                return None

        df = await self._c.call(call, "get_concept_ths")
        items: list[dict] = []
        for row in _rows(df):
            index_code = _code(row.get("concept_code"))
            name = _str(row.get("name"))
            if not index_code or not name:
                continue
            items.append({
                "symbol": symbol,
                "index_code": index_code,
                "name": name,
                "reason": _str(row.get("reason")),
            })
        return items


__all__ = ["StockConceptsAdataFetcher"]
