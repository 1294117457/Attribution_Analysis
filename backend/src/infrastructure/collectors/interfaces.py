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
    list_status: str = "L"  # 上市状态（L/D/P）


@runtime_checkable
class FetcherProtocol(Protocol):
    """采集器协议

    所有数据源适配器必须满足此协议。
    """

    def fetch(self, params: CollectParams) -> list[Any]:
        """执行 K 线采集"""
        ...

    def fetch_stock_basic(self, params: CollectParams) -> list[Any]:
        """执行股票基本信息采集（stock_basic）

        返回领域 BO 列表，由调用方转换为实体。
        """
        ...

    @property
    def source_name(self) -> str:
        """数据源名称"""
        ...
