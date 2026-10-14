"""adata · 同花顺概念 Adapter（6 个）

"接口正常但无数据"返回空列表，与"失败"（抛异常）区分 —— 成分股任务据此决定是否删除旧关系。
"""
from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any, Optional

import pandas as pd

from contexts.data.application.port.concept import (
    ConceptIndexDailyParams,
    ConceptIndexDailyPort,
    ConceptIndexTHBO,
    ConceptListBO,
    ConceptListPort,
    ConceptMemberBO,
    ConceptMembersPort,
    ConceptMinuteBO,
    ConceptMinutePoint,
    ConceptMinutePort,
    ConceptOfStockBO,
    ConceptSnapshotBO,
    ConceptSnapshotPort,
    StockConceptsPort,
)
from contexts.data.application.port.types import EmptyParams, IndexCodeParams, SymbolParams
from contexts.data.infrastructure.adapter.adata.client import AdataClient
from contexts.data.infrastructure.adapter.core.base import AdapterBase


class AdataAdapterBase(AdapterBase):
    tool = "adata"
    origin = "ths"
    priority = 10
    throttle_group = "adata:ths"

    def __init__(self, client: AdataClient) -> None:
        self._c = client

    @property
    def _sdk(self) -> Any:
        return self._c.sdk


class AdataConceptListAdapter(ConceptListPort, AdataAdapterBase):
    async def fetch(self, p: EmptyParams) -> list[ConceptListBO]:
        """丢弃 index_code 为空的行（问财接口偶发缺失）"""
        df = await self._c.call(lambda: self._sdk.stock.info.all_concept_code_ths(), "all_concept_code_ths")
        items: list[ConceptListBO] = []
        seen: set[str] = set()
        for row in _rows(df):
            index_code = _code(row.get("index_code"))
            name = _str(row.get("name"))
            if not index_code or not name or index_code in seen:
                continue
            seen.add(index_code)
            items.append(ConceptListBO(index_code=index_code, concept_code=_code(row.get("concept_code")), name=name))
        return items


class AdataConceptMembersAdapter(ConceptMembersPort, AdataAdapterBase):
    async def fetch(self, p: IndexCodeParams) -> list[ConceptMemberBO]:
        """去重保序"""
        df = await self._c.call(
            lambda: self._sdk.stock.info.concept_constituent_ths(index_code=p.index_code),
            "concept_constituent_ths",
        )
        items: list[ConceptMemberBO] = []
        seen: set[str] = set()
        for row in _rows(df):
            symbol = _symbol(row.get("stock_code"))
            if symbol and symbol not in seen:
                seen.add(symbol)
                items.append(ConceptMemberBO(index_code=p.index_code, symbol=symbol))
        return items


class AdataStockConceptsAdapter(StockConceptsPort, AdataAdapterBase):
    async def fetch(self, p: SymbolParams) -> list[ConceptOfStockBO]:
        def call():
            try:
                return self._sdk.stock.info.get_concept_ths(stock_code=p.symbol)
            except AttributeError:
                # F10 页面没有概念表格（无概念 / 新股）时 adata 内部 None.tbody
                return None

        df = await self._c.call(call, "get_concept_ths")
        items: list[ConceptOfStockBO] = []
        for row in _rows(df):
            index_code = _code(row.get("concept_code"))
            name = _str(row.get("name"))
            if not index_code or not name:
                continue
            items.append(ConceptOfStockBO(
                symbol=p.symbol, index_code=index_code, name=name, reason=_str(row.get("reason")),
            ))
        return items


class AdataConceptIndexDailyAdapter(ConceptIndexDailyPort, AdataAdapterBase):
    async def fetch(self, p: ConceptIndexDailyParams) -> list[ConceptIndexTHBO]:
        """接口无日期参数，总是返回全部历史"""
        df = await self._c.call(
            lambda: self._sdk.stock.market.get_market_concept_ths(index_code=p.index_code, k_type=1),
            "get_market_concept_ths",
        )
        items: list[ConceptIndexTHBO] = []
        for row in _rows(df):
            trade_date = _date(row.get("trade_date"))
            close = _float(row.get("close"))
            if trade_date is None or close is None:
                continue
            items.append(ConceptIndexTHBO(
                index_code=p.index_code,
                concept_name=p.concept_name,
                trade_date=trade_date,
                open=_float(row.get("open")) or 0.0,
                high=_float(row.get("high")) or 0.0,
                low=_float(row.get("low")) or 0.0,
                close=close,
                volume=int(_float(row.get("volume")) or 0),
                amount=_float(row.get("amount")) or 0.0,
                change=_float(row.get("change")),
                change_pct=_float(row.get("change_pct")),
            ))
        return items


class AdataConceptSnapshotAdapter(ConceptSnapshotPort, AdataAdapterBase):
    async def fetch(self, p: IndexCodeParams) -> list[ConceptSnapshotBO]:
        df = await self._c.call(
            lambda: self._sdk.stock.market.get_market_concept_current_ths(index_code=p.index_code),
            "get_market_concept_current_ths",
        )
        for row in _rows(df):
            return [ConceptSnapshotBO(
                index_code=p.index_code,
                price=_float(row.get("price")),
                change=_float(row.get("change")),
                change_pct=_float(row.get("change_pct")),
                volume=_float(row.get("volume")),
                amount=_float(row.get("amount")),
                open=_float(row.get("open")),
                high=_float(row.get("high")),
                low=_float(row.get("low")),
                prev_close=_float(row.get("prev_close")),
                turnover_rate=_float(row.get("turnover_rate")),
                pe=_float(row.get("pe")),
                pb=_float(row.get("pb")),
                trade_time=_str(row.get("trade_time")),
            )]
        return []


class AdataConceptMinuteAdapter(ConceptMinutePort, AdataAdapterBase):
    async def fetch(self, p: IndexCodeParams) -> list[ConceptMinuteBO]:
        df = await self._c.call(
            lambda: self._sdk.stock.market.get_market_concept_min_ths(index_code=p.index_code),
            "get_market_concept_min_ths",
        )
        points: list[ConceptMinutePoint] = []
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
            points.append(ConceptMinutePoint(
                trade_time=trade_time.strftime("%H:%M") if trade_time else _str(row.get("trade_time")) or "",
                price=price,
                avg_price=_float(row.get("avg_price")),
                volume=int(volume) if volume is not None else None,
                amount=_float(row.get("amount")),
                change_pct=_float(row.get("change_pct")),
            ))
            last = {
                "price": price,
                "change": change,
                "change_pct": _float(row.get("change_pct")),
                "trade_time": trade_time.strftime("%Y-%m-%d %H:%M") if trade_time else None,
            }
            trade_date = _str(row.get("trade_date")) or trade_date
        if not points:
            return []
        return [ConceptMinuteBO(
            index_code=p.index_code,
            trade_date=trade_date,
            pre_close=pre_close,
            price=last["price"],
            change=last["change"],
            change_pct=last["change_pct"],
            trade_time=last["trade_time"],
            points=points,
        )]


ADAPTERS = (
    AdataConceptListAdapter,
    AdataConceptMembersAdapter,
    AdataStockConceptsAdapter,
    AdataConceptIndexDailyAdapter,
    AdataConceptSnapshotAdapter,
    AdataConceptMinuteAdapter,
)


# ── 解析辅助 ───────────────────────────────────────────


def _rows(df) -> list[dict]:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return []
    return df.to_dict("records")


def _is_missing(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v)) or (isinstance(v, str) and not v.strip())


def _str(v) -> Optional[str]:
    if _is_missing(v):
        return None
    return str(v).strip() or None


def _code(v) -> Optional[str]:
    s = _str(v)
    if s is None:
        return None
    if s.endswith(".0"):
        s = s[:-2]
    return s


def _symbol(v) -> Optional[str]:
    s = _code(v)
    if s is None:
        return None
    s = s.zfill(6)
    return s if len(s) == 6 and s.isdigit() else None


def _float(v) -> Optional[float]:
    if _is_missing(v):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _date(v) -> Optional[date]:
    if _is_missing(v):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _datetime(v) -> Optional[datetime]:
    if _is_missing(v):
        return None
    if isinstance(v, datetime):
        return v
    try:
        return datetime.strptime(str(v)[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


__all__ = ["ADAPTERS", "AdataAdapterBase"]
