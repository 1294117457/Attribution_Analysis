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


def to_ts_code(symbol: str) -> str:
    """6 位 A 股代码 → Tushare ts_code

    - 000001 → 000001.SZ
    - 600000 → 600000.SH
    - 688001 → 688001.SH
    - 920xxx / 83xxxx / 87xxxx / 43xxxx / 82xxxx → .BJ

    入参已带后缀（"000001.SZ"）时按后缀原样返回（大写）。

    Raises:
        ValueError: 代码格式非法
    """
    if not symbol:
        raise ValueError("股票代码不能为空")
    s = str(symbol).strip()

    # 已带后缀
    if "." in s:
        code, _, suffix = s.partition(".")
        suffix = suffix.upper()
        if len(code) != 6 or not code.isdigit():
            raise ValueError(f"无效的股票代码: {symbol!r}，应为 6 位数字")
        if suffix not in ("SZ", "SH", "BJ"):
            raise ValueError(
                f"无效的交易所后缀: {symbol!r}（应为 SZ / SH / BJ）"
            )
        return f"{code}.{suffix}"

    if len(s) != 6 or not s.isdigit():
        raise ValueError(f"无效的股票代码: {symbol!r}，应为 6 位数字")

    prefix2, prefix3 = s[:2], s[:3]

    # 北交所：老代码 83/87/43/82，2024 年起新代码段 920xxx
    if prefix2 in ("83", "87", "43", "82", "92"):
        return f"{s}.BJ"

    if prefix3 in ("600", "601", "603", "605", "688", "689"):
        return f"{s}.SH"

    return f"{s}.SZ"


__all__ = [
    "IndexCode",
    "Symbol",
    "TradeDate",
    "to_ts_code",
]
