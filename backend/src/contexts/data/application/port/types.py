"""data.application.port.types — data 自己的 Params 类型

公共类型（Symbol/TradeDate/IndexCode）已搬到 shared.interface.validators。
这里只放 data context 自己的 Params。
"""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

# 重新导出公共类型（保持 data 内部使用方便）
from shared.interface.validators import IndexCode, Symbol, TradeDate


class ListStatus(StrEnum):
    LISTED = "L"
    DELISTED = "D"
    PAUSED = "P"


class EmptyParams(BaseModel):
    """空参数（拉全市场）"""
    model_config = ConfigDict(extra="forbid")


class TradeDateParams(BaseModel):
    """按交易日全市场拉取"""
    model_config = ConfigDict(extra="forbid")
    trade_date: TradeDate


class SymbolParams(BaseModel):
    """按单只股票拉取"""
    model_config = ConfigDict(extra="forbid")
    symbol: Symbol


class IndexCodeParams(BaseModel):
    """按单个概念指数拉取"""
    model_config = ConfigDict(extra="forbid")
    index_code: IndexCode


__all__ = [
    "EmptyParams",
    "IndexCode",
    "IndexCodeParams",
    "ListStatus",
    "Symbol",
    "SymbolParams",
    "TradeDate",
    "TradeDateParams",
]
