"""K线值对象"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Optional

from shared.domain.base import ValueObject


@dataclass(frozen=True)
class StockCode(ValueObject):
    """股票代码值对象

    6 位数字（A 股代码）。
    """

    code: str

    def __post_init__(self) -> None:
        if not self._validate(self.code):
            raise ValueError(f"无效的股票代码: {self.code}")

    @staticmethod
    def _validate(code: str) -> bool:
        if not code:
            return False
        return bool(re.match(r"^\d{6}$", code))

    def _get_values(self) -> tuple:
        return (self.code,)

    @property
    def is_shanghai(self) -> bool:
        return self.code.startswith(("6", "5"))

    @property
    def is_shenzhen(self) -> bool:
        return self.code.startswith(("0", "3"))


@dataclass(frozen=True)
class TradeDate(ValueObject):
    """交易日期值对象"""

    date: date

    def _get_values(self) -> tuple:
        return (self.date,)

    @property
    def is_weekend(self) -> bool:
        return self.date.weekday() >= 5

    def to_string(self, fmt: str = "%Y-%m-%d") -> str:
        return self.date.strftime(fmt)


@dataclass(frozen=True)
class IndicatorValues(ValueObject):
    """某一交易日的技术指标（由 K 线序列实时计算的派生值，数据不足时为 None）"""

    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None
    ema12: Optional[float] = None
    ema26: Optional[float] = None
    macd_dif: Optional[float] = None
    macd_dea: Optional[float] = None
    macd_bar: Optional[float] = None
    rsi6: Optional[float] = None
    rsi12: Optional[float] = None
    rsi24: Optional[float] = None
    kdj_k: Optional[float] = None
    kdj_d: Optional[float] = None
    kdj_j: Optional[float] = None
    boll_up: Optional[float] = None
    boll_mid: Optional[float] = None
    boll_dn: Optional[float] = None

    def _get_values(self) -> tuple:
        return tuple(self.to_dict().values())

    def to_dict(self) -> dict[str, Optional[float]]:
        return {
            "ma5": self.ma5, "ma10": self.ma10, "ma20": self.ma20, "ma60": self.ma60,
            "ema12": self.ema12, "ema26": self.ema26,
            "macd_dif": self.macd_dif, "macd_dea": self.macd_dea, "macd_bar": self.macd_bar,
            "rsi6": self.rsi6, "rsi12": self.rsi12, "rsi24": self.rsi24,
            "kdj_k": self.kdj_k, "kdj_d": self.kdj_d, "kdj_j": self.kdj_j,
            "boll_up": self.boll_up, "boll_mid": self.boll_mid, "boll_dn": self.boll_dn,
        }
