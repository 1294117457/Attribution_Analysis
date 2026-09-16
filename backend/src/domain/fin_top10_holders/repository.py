"""fin_top10_holders — 仓储接口"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from domain.fin_top10_holders.entity import FinTop10Holder


class FinTop10HolderRepository(ABC):
    @abstractmethod
    async def save(self, entity: FinTop10Holder) -> FinTop10Holder: ...
    @abstractmethod
    async def save_batch(self, entities: list[FinTop10Holder]) -> int: ...
    @abstractmethod
    async def find_by_symbol(
        self,
        symbol: str,
        end_date: Optional[date] = None,
    ) -> list[FinTop10Holder]: ...
