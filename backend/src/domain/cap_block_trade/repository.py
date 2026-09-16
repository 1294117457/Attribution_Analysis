"""cap_block_trade — 仓储接口"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from domain.cap_block_trade.entity import CapBlockTrade


class CapBlockTradeRepository(ABC):
    @abstractmethod
    async def save_batch(self, entities: list[CapBlockTrade]) -> int: ...
    @abstractmethod
    async def find_by_symbol(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[CapBlockTrade]: ...
