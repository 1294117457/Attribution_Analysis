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
    """市场值对象（市场类型：主板/创业板/科创板/北交所）"""

    code: str  # 标准化代码：MAIN/STAR/CHINEXT/BSE
    name: str  # 中文显示名

    def _get_values(self) -> tuple:
        return (self.code, self.name)

    @property
    def is_main_board(self) -> bool:
        return self.code == "MAIN"

    @property
    def is_star(self) -> bool:
        return self.code == "STAR"

    @property
    def is_chinext(self) -> bool:
        return self.code == "CHINEXT"

    @property
    def is_bse(self) -> bool:
        return self.code == "BSE"

    @classmethod
    def from_market_type(cls, type_str: str) -> "Market":
        """根据 Tushare market 字符串解析

        Tushare market 取值：
        - 主板 / 普通股
        - 中小板（已并入主板）
        - 创业板
        - 科创板
        - CDR
        - 北交所
        """
        mapping: dict[str, tuple[str, str]] = {
            "主板":   ("MAIN",     "主板"),
            "中小板": ("MAIN",     "中小板"),
            "普通股": ("MAIN",     "主板"),
            "创业板": ("CHINEXT",  "创业板"),
            "科创板": ("STAR",     "科创板"),
            "CDR":   ("CDR",      "CDR"),
            "北交所": ("BSE",      "北交所"),
        }
        s = (type_str or "").strip()
        if s in mapping:
            code, name = mapping[s]
            return cls(code, name)
        # 兜底：未知类型用原文
        return cls("OTHER", s or "—")

    @classmethod
    def from_exchange(cls, exchange: str) -> "Market":
        """根据交易所代码（SSE/SZSE/BSE）推断市场类型"""
        mapping = {
            "SSE":  cls("MAIN", "主板"),
            "SZSE": cls("MAIN", "主板"),
            "BSE":  cls("BSE",  "北交所"),
        }
        return mapping.get((exchange or "").upper(), cls("OTHER", "—"))
