"""base_adj_factor — 仓储接口"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from domain.base_adj_factor.entity import BaseAdjFactor


class BaseAdjFactorRepository(ABC):
    @abstractmethod
    async def save(self, entity: BaseAdjFactor) -> BaseAdjFactor: ...
    @abstractmethod
    async def save_batch(self, entities: list[BaseAdjFactor]) -> int: ...
    @abstractmethod
    async def find_by_symbol(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[BaseAdjFactor]: ...
