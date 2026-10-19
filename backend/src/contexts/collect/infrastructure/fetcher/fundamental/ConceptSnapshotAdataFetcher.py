"""ConceptSnapshotAdataFetcher：概念行情快照（同花顺 adata get_market_concept_current_ths）—— step7 重构版"""
from __future__ import annotations

from pydantic import BaseModel

from contexts.collect.infrastructure.fetcher.base import BaseFetcher
from contexts.collect.infrastructure.connect.adata_client import get_adata_client
from contexts.collect.infrastructure.fetcher.fundamental.ConceptListAdataFetcher import (
    _float, _rows, _str,
)


class ConceptSnapshotAdataFetcher(BaseFetcher):
    fetcher_type = "concept_snapshot_adata"
    source = "adata"
    label = "概念行情快照（同花顺 adata）"

    def __init__(self) -> None:
        self._c = get_adata_client()
        self._sdk = self._c.sdk

    async def fetch(self, **params) -> list[BaseModel]:
        index_code = params.get("index_code")
        if not index_code:
            raise ValueError("index_code 必填")
        df = await self._c.call(
            lambda: self._sdk.stock.market.get_market_concept_current_ths(index_code=index_code),
            "get_market_concept_current_ths",
        )
        for row in _rows(df):
            return [{
                "index_code": index_code,
                # §1.7 字段语义修复 + 补 trade_date / concept_name
                "concept_name": _str(row.get("name")),
                "trade_date": _str(row.get("trade_date")),
                "price": _float(row.get("price")),
                "open_price": _float(row.get("open")),
                "high": _float(row.get("high")),
                "low": _float(row.get("low")),
                "prev_close": _float(row.get("prev_close")),
                "p_change": _float(row.get("change")),
                "pct_change": _float(row.get("change_pct")),
                "volume": _float(row.get("volume")),
                "amount": _float(row.get("amount")),
                "turnover_rate": _float(row.get("turnover_rate")),
                "pe": _float(row.get("pe")),
                "pb": _float(row.get("pb")),
                "trade_time": _str(row.get("trade_time")),
            }]
        return []


__all__ = ["ConceptSnapshotAdataFetcher"]
