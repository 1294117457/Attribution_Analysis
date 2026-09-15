"""操作池 - 值对象"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from domain.base import ValueObject


# ═══════════════════════════════════════════════════════════════════════════════
# PoolType - 池类型
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class PoolType(ValueObject):
    """池类型值对象（不可变）"""

    code: str
    label: str

    def _get_values(self) -> tuple:
        return (self.code,)

    WATCHLIST = None
    INDUSTRY = None
    STRATEGY = None
    CUSTOM = None

    @classmethod
    def _init_constants(cls) -> None:
        cls.WATCHLIST = cls("watchlist", "自选股")
        cls.INDUSTRY = cls("industry", "行业")
        cls.STRATEGY = cls("strategy", "策略")
        cls.CUSTOM = cls("custom", "自定义")

    @classmethod
    def from_code(cls, code: str) -> PoolType:
        """从代码创建值对象（未识别代码返回 CUSTOM）"""
        mapping = {
            "watchlist": cls.WATCHLIST,
            "industry": cls.INDUSTRY,
            "strategy": cls.STRATEGY,
            "custom": cls.CUSTOM,
        }
        return mapping.get(code.lower(), cls.CUSTOM)

    @classmethod
    def all(cls) -> tuple[PoolType, ...]:
        return (cls.WATCHLIST, cls.INDUSTRY, cls.STRATEGY, cls.CUSTOM)

    @property
    def is_system(self) -> bool:
        return self.code in ("watchlist", "industry", "strategy")


PoolType._init_constants()


# ═══════════════════════════════════════════════════════════════════════════════
# PoolColor - 展示颜色
# ═══════════════════════════════════════════════════════════════════════════════


HEX_PATTERN = __import__("re").compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True)
class PoolColor(ValueObject):
    """池展示颜色值对象（不可变）"""

    hex_code: str

    def _get_values(self) -> tuple:
        return (self.hex_code,)

    def __post_init__(self) -> None:
        if self.hex_code and not HEX_PATTERN.match(self.hex_code):
            raise ValueError(f"无效的 HEX 颜色码: {self.hex_code}")

    @classmethod
    def from_hex(cls, hex_code: str | None) -> Optional[PoolColor]:
        if not hex_code:
            return None
        return cls(hex_code.upper())

    @property
    def css_value(self) -> str:
        return self.hex_code or "#1890ff"


# ═══════════════════════════════════════════════════════════════════════════════
# OperationStatus - 操作状态
# ═══════════════════════════════════════════════════════════════════════════════


class OperationStatus(Enum):
    """池操作状态枚举"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        """是否终态"""
        return self in (
            OperationStatus.SUCCESS,
            OperationStatus.PARTIAL,
            OperationStatus.FAILED,
            OperationStatus.CANCELLED,
        )

    @property
    def is_active(self) -> bool:
        """是否进行中"""
        return self in (OperationStatus.PENDING, OperationStatus.RUNNING)


# ═══════════════════════════════════════════════════════════════════════════════
# OperationType - 操作类型
# ═══════════════════════════════════════════════════════════════════════════════


class OperationType(Enum):
    """池操作类型枚举"""

    KLINE_COLLECT = "kline_collect"
    NEWS_FETCH = "news_fetch"
    FACTOR_CALC = "factor_calc"

    @classmethod
    def from_code(cls, code: str) -> OperationType:
        mapping = {e.value: e for e in cls}
        if code not in mapping:
            raise ValueError(f"未知操作类型: {code}")
        return mapping[code]

    @property
    def is_implemented(self) -> bool:
        return self == OperationType.KLINE_COLLECT


# ═══════════════════════════════════════════════════════════════════════════════
# PoolMember - 池成员值对象
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class PoolMember(ValueObject):
    """池成员值对象（不可变）"""

    symbol: str
    memo: str = ""
    sort_order: int = 0
    added_at: Optional[datetime] = None

    def _get_values(self) -> tuple:
        return (self.symbol, self.memo, self.sort_order)

    def __post_init__(self) -> None:
        if not self.symbol or not self.symbol.strip():
            raise ValueError("股票代码不能为空")
        if len(self.symbol) != 6 or not self.symbol.isdigit():
            raise ValueError(f"无效的股票代码: {self.symbol}")

    @property
    def has_memo(self) -> bool:
        return bool(self.memo)
