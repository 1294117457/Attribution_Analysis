"""实时接口：概念当日分时 / 实时行情（adata · 同花顺 get_market_concept_min_ths，不入库）

与概念清单 / 成分股 / 日 K 同源，以 index_code（885xxx）为键。
行情头部（price / change_pct）与分时共用同一条缓存。
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from application.port.collector_port import ConceptFetcher
from infrastructure.adapter import get_registry
from infrastructure.adapter.realtime.base import BaseRealtimeQuery
from infrastructure.persistence.connection import AsyncSessionLocal
from infrastructure.persistence.repositories.concept_repository import ConceptRepoImpl


class ConceptMinuteQuery(BaseRealtimeQuery):
    name = "concept_minute"
    facet = "fundamental"
    sub_facet = "concept"
    label = "概念实时行情"
    description = "同花顺概念当日分时（241 点）+ 最新涨跌幅；失败时降级为最近一条日 K 收盘"
    sort_order = 10
    source = "ths"
    source_label = "同花顺"
    ttl_trading = 15
    consumers = ("详情抽屉 · 概念 Tab",)
    sample_params = {"index_code": "885525"}

    def normalize(self, params: dict) -> dict:
        index_code = str(params.get("index_code") or "").strip()
        if not index_code.isdigit() or len(index_code) != 6:
            raise ValueError("index_code 需为 6 位同花顺指数编码（885xxx）")
        return {"index_code": index_code}

    def cache_key(self, params: dict) -> str:
        return params["index_code"]

    async def fetch(self, params: dict) -> Optional[dict[str, Any]]:
        fetcher: ConceptFetcher = get_registry().get(ConceptFetcher)
        bo = await asyncio.to_thread(fetcher.fetch_minute, params["index_code"])
        return bo.model_dump() if bo is not None else None

    async def fallback(self, params: dict) -> Optional[dict[str, Any]]:
        index_code = params["index_code"]
        async with AsyncSessionLocal() as session:
            closes = await ConceptRepoImpl(session).get_latest_closes([index_code])
        row = closes.get(index_code)
        if not row or row.get("close") is None:
            return None
        close, change = row["close"], row.get("change")
        trade_date = row.get("trade_date")
        return {
            "index_code": index_code,
            "trade_date": str(trade_date) if trade_date else None,
            "pre_close": round(close - change, 4) if change is not None else None,
            "price": close,
            "change": change,
            "change_pct": row.get("change_pct"),
            "trade_time": str(trade_date) if trade_date else None,
            "points": [],
        }
