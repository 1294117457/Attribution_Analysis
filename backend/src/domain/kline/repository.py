"""K线仓储接口（Protocol 定义在领域层）"""

from __future__ import annotations

from datetime import date
from typing import Optional, Protocol, runtime_checkable

from domain.kline.entity import Kline
from domain.kline.value_objects import StockCode


@runtime_checkable
class KlineRepository(Protocol):
    """K线仓储接口

    实现类放在 infrastructure/repositories/。
    领域层不关心具体持久化方式。
    """

    async def save(self, kline: Kline) -> Kline: ...
    async def save_batch(self, klines: list[Kline]) -> int: ...
    async def find_by_id(self, id: int) -> Optional[Kline]: ...
    async def find_by_symbol_date(
        self, symbol: StockCode, trade_date: date
    ) -> Optional[Kline]: ...
    async def find_by_symbol(
        self,
        symbol: StockCode,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 365,
        order_desc: bool = True,
    ) -> list[Kline]: ...
    async def count_by_symbol(self, symbol: StockCode) -> int: ...
    async def delete_by_symbol(self, symbol: StockCode) -> int: ...
    async def delete_one(self, symbol: StockCode, trade_date: date) -> int: ...
