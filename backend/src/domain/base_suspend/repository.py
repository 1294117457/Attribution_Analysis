"""base_suspend — 仓储接口"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from domain.base_suspend.entity import BaseSuspend


class BaseSuspendRepository(ABC):
    @abstractmethod
    async def save(self, entity: BaseSuspend) -> BaseSuspend: ...
    @abstractmethod
    async def save_batch(self, entities: list[BaseSuspend]) -> int: ...
    @abstractmethod
    async def find_by_symbol(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[BaseSuspend]: ...
