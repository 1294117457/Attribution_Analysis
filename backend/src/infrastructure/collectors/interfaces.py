"""采集器接口定义

ACL（Anti-Corruption Layer）防腐层对外的统一接口。
所有数据源适配器必须实现 FetcherProtocol。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional, Protocol, runtime_checkable, Any


@dataclass
class CollectParams:
    """通用采集参数"""

    symbol: Optional[str] = None
    keyword: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    days: int = 30
    adjust: str = "qfq"


@runtime_checkable
class FetcherProtocol(Protocol):
    """采集器协议

    所有数据源适配器必须满足此协议。
    fetch() 返回值类型：list[KlineBO]（或其他领域 BO）
    """

    def fetch(self, params: CollectParams) -> list[Any]:
        """执行采集"""
        ...

    @property
    def source_name(self) -> str:
        """数据源名称"""
        ...
