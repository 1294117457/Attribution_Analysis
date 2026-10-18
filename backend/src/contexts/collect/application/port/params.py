"""port 契约的参数类型（Pydantic 模型）

业务语义化的入参，不含 SDK 特有字段（如 ts_code / "20261013"）。
转换在 fetcher 内做。
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from shared.interface.validators import IndexCode, Symbol, TradeDate


class ListStatus(StrEnum):
    LISTED = "L"
    DELISTED = "D"
    PAUSED = "P"


class EmptyParams(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TradeDateParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trade_date: TradeDate


class SymbolParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: Symbol


class IndexCodeParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    index_code: IndexCode


class StockBasicParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    list_status: ListStatus = ListStatus.LISTED


class MinuteKlineParams(BaseModel):
    """分 K 线入参（实时接口专用）"""
    model_config = ConfigDict(extra="forbid")
    symbol: str
    interval: str = "5min"
    days: int = 1


__all__ = [
    "EmptyParams", "IndexCodeParams", "ListStatus", "MinuteKlineParams",
    "StockBasicParams", "SymbolParams", "TradeDateParams",
]
