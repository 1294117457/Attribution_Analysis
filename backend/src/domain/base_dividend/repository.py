"""base_dividend — 仓储接口"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from domain.base_dividend.entity import BaseDividend


class BaseDividendRepository(ABC):
    @abstractmethod
    async def save(self, entity: BaseDividend) -> BaseDividend: ...
    @abstractmethod
    async def save_batch(self, entities: list[BaseDividend]) -> int: ...
    @abstractmethod
    async def find_by_symbol(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[BaseDividend]: ...
