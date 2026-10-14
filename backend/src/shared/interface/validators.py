"""shared.interface.validators — 跨 context 共享的数据校验类型

- Symbol: A 股股票代码（6 位数字）
- IndexCode: 同花顺指数编码（885xxx 等）
- TradeDate: 交易日（支持 "YYYY-MM-DD" / "YYYYMMDD" / date / datetime）

从 contexts/data/application/port/types.py 提取（step7-c）。
"""
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


__all__ = [
    "IndexCode",
    "Symbol",
    "TradeDate",
]
