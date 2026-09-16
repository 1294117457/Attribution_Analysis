"""cap_margin_detail — 仓储接口"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from domain.cap_margin_detail.entity import CapMarginDetail


class CapMarginDetailRepository(ABC):
    @abstractmethod
    async def save(self, entity: CapMarginDetail) -> CapMarginDetail: ...
    @abstractmethod
    async def save_batch(self, entities: list[CapMarginDetail]) -> int: ...
    @abstractmethod
    async def find_by_symbol_date(
        self, symbol: str, trade_date: date
    ) -> Optional[CapMarginDetail]: ...
    @abstractmethod
    async def find_by_symbol(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[CapMarginDetail]: ...
