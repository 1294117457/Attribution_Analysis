"""Fetcher 接口定义"""

from typing import Protocol
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from data.schemas.base import BaseData


@dataclass
class CollectParams:
    """采集参数"""

    symbol: Optional[str] = None
    keyword: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    days: int = 30


class FetcherProtocol(Protocol):
    """Fetcher 接口：所有数据源适配器必须满足此协议"""

    def fetch(self, params: CollectParams) -> list[BaseData]:
        """执行采集，返回 BaseData 子类列表"""
        ...
