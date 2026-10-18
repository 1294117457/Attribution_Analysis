"""ConceptMinuteAdataFetcher：概念实时分时（同花顺 adata get_market_concept_min_ths）—— step7 重构版"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from contexts.collect.infrastructure.fetcher.base import BaseFetcher
from contexts.collect.infrastructure.connect.adata_client import get_adata_client
from contexts.collect.infrastructure.fetcher.fundamental.ConceptListAdataFetcher import (
    _datetime, _float, _rows, _str,
)


class ConceptMinuteAdataFetcher(BaseFetcher):
    fetcher_type = "concept_minute_adata"
    source = "adata"
    label = "概念实时分时（同花顺 adata）"

    def __init__(self) -> None:
        self._c = get_adata_client()
        self._sdk = self._c.sdk

    async def fetch(self, **params) -> list[BaseModel]:
        index_code = params.get("index_code")
        if not index_code:
            raise ValueError("index_code 必填")
        df = await self._c.call(
            lambda: self._sdk.stock.market.get_market_concept_min_ths(index_code=index_code),
            "get_market_concept_min_ths",
        )
        points: list[dict] = []
        pre_close: Optional[float] = None
        last: dict = {}
        trade_date: Optional[str] = None
        for row in _rows(df):
            price = _float(row.get("price"))
            if price is None:
                continue
            change = _float(row.get("change"))
            if pre_close is None and change is not None:
                pre_close = round(price - change, 4)
            volume = _float(row.get("volume"))
            trade_time = _datetime(row.get("trade_time"))
            points.append({
                "trade_time": trade_time.strftime("%H:%M") if trade_time else _str(row.get("trade_time")) or "",
                "price": price,
                "avg_price": _float(row.get("avg_price")),
                "volume": int(volume) if volume is not None else None,
                "amount": _float(row.get("amount")),
                "change_pct": _float(row.get("change_pct")),
            })
            last = {
                "price": price,
                "change": change,
                "change_pct": _float(row.get("change_pct")),
                "trade_time": trade_time.strftime("%Y-%m-%d %H:%M") if trade_time else None,
            }
            trade_date = _str(row.get("trade_date")) or trade_date
        if not points:
            return []
        return [{
            "index_code": index_code,
            "trade_date": trade_date,
            "pre_close": pre_close,
            "price": last["price"],
            "change": last["change"],
            "change_pct": last["change_pct"],
            "trade_time": last["trade_time"],
            "points": points,
        }]


__all__ = ["ConceptMinuteAdataFetcher"]
