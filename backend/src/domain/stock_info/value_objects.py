"""股票信息值对象"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from domain.base import ValueObject


@dataclass(frozen=True)
class Industry(ValueObject):
    """行业值对象"""

    name: str

    def _get_values(self) -> tuple:
        return (self.name,)


@dataclass(frozen=True)
class Market(ValueObject):
    """市场值对象"""

    code: str
    name: str

    SHANGHAI = None      # 在模块加载时初始化
    SHENZHEN = None
    BSE = None

    def _get_values(self) -> tuple:
        return (self.code, self.name)

    @property
    def is_shanghai(self) -> bool:
        return self.code == "SH"

    @property
    def is_shenzhen(self) -> bool:
        return self.code in ("SZ", "BSE")

    @classmethod
    def from_code(cls, code: str) -> "Market":
        """根据代码获取市场"""
        mapping = {
            "SH": cls("SH", "上海证券交易所"),
            "SZ": cls("SZ", "深圳证券交易所"),
            "BSE": cls("BSE", "北京证券交易所"),
        }
        return mapping.get(code.upper(), cls("SZ", "深圳证券交易所"))
