"""ConceptIndexDailyAdataFetcher：概念指数日 K（同花顺 adata get_market_concept_ths）—— step7 重构版"""
from __future__ import annotations

from pydantic import BaseModel

from collectors.base import BaseFetcher
from core.adata_client import get_adata_client
from collectors.fundamental.ConceptListAdataFetcher import (
    _date, _float, _rows,
)


class ConceptIndexDailyAdataFetcher(BaseFetcher):
    fetcher_type = "concept_index_daily_adata"
    source = "adata"
    label = "概念指数日 K（同花顺 adata）"

    def __init__(self) -> None:
        self._c = get_adata_client()
        self._sdk = self._c.sdk

    async def fetch(self, **params) -> list[BaseModel]:
        index_code = params.get("index_code")
        concept_name = params.get("concept_name", "")
        if not index_code:
            raise ValueError("index_code 必填")
        df = await self._c.call(
            lambda: self._sdk.stock.market.get_market_concept_ths(index_code=index_code, k_type=1),
            "get_market_concept_ths",
        )
        items: list[dict] = []
        for row in _rows(df):
            td = _date(row.get("trade_date"))
            close = _float(row.get("close"))
            if td is None or close is None:
                continue
            items.append({
                "index_code": index_code,
                "concept_name": concept_name,
                "trade_date": td.isoformat(),
                "open": _float(row.get("open")) or 0.0,
                "high": _float(row.get("high")) or 0.0,
                "low": _float(row.get("low")) or 0.0,
                "close": close,
                "volume": int(_float(row.get("volume")) or 0),
                "amount": _float(row.get("amount")) or 0.0,
                "change": _float(row.get("change")),
                "change_pct": _float(row.get("change_pct")),
            })
        return items


__all__ = ["ConceptIndexDailyAdataFetcher"]
