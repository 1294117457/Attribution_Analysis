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
    async def bulk_upsert(self, stocks: list[StockInfo]) -> int: ...
    async def delete(self, symbol: str) -> bool: ...
    async def list_with_kline_stats(
        self,
        industry: Optional[str] = None,
        market: Optional[str] = None,
    ) -> list[dict]: ...
    async def list_paginated(
        self,
        q: Optional[str] = None,
        industry: Optional[str] = None,
        market: Optional[str] = None,
        exchange: Optional[str] = None,
        is_hs: Optional[str] = None,
        list_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[StockInfo], int]: ...
    async def list_with_kline_stats_paginated(
        self,
        q: Optional[str] = None,
        industry: Optional[str] = None,
        market: Optional[str] = None,
        exchange: Optional[str] = None,
        is_hs: Optional[str] = None,
        list_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]: ...
    async def distinct_meta(self) -> dict[str, list[str]]: ...
