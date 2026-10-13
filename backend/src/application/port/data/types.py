"""Port 参数的公共类型"""
from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, StringConstraints


def _parse_trade_date(v: Any) -> Any:
    """date / datetime / "YYYY-MM-DD" / "YYYYMMDD" → date（其余交给 pydantic 校验）"""
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        s = v.strip()
        if len(s) == 8 and s.isdigit():
            return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        return s
    return v


Symbol = Annotated[str, StringConstraints(pattern=r"^\d{6}$")]
IndexCode = Annotated[str, StringConstraints(pattern=r"^\d{6}$")]
TradeDate = Annotated[date, BeforeValidator(_parse_trade_date)]


class ListStatus(StrEnum):
    LISTED = "L"
    DELISTED = "D"
    PAUSED = "P"


class EmptyParams(BaseModel):
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
