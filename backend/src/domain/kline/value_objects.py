"""K线值对象"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Optional

from domain.base import ValueObject


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
