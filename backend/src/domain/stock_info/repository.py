"""股票信息仓储接口"""

from __future__ import annotations

from datetime import date
from typing import Optional, Protocol, runtime_checkable

from domain.stock_info.entity import StockInfo


@runtime_checkable
class StockInfoRepository(Protocol):
    """股票信息仓储接口"""

    async def save(self, stock: StockInfo) -> StockInfo: ...
    async def find_by_symbol(self, symbol: str) -> Optional[StockInfo]: ...
    async def find_all(
        self,
        industry: Optional[str] = None,
        market: Optional[str] = None,
    ) -> list[StockInfo]: ...
    async def upsert(self, stock: StockInfo) -> StockInfo: ...
    async def delete(self, symbol: str) -> bool: ...
    async def list_with_kline_stats(
        self,
        industry: Optional[str] = None,
        market: Optional[str] = None,
    ) -> list[dict]: ...
