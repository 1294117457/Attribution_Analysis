"""fin_top10_float — 仓储接口"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from domain.fin_top10_float.entity import FinTop10FloatHolder


class FinTop10FloatHolderRepository(ABC):
    @abstractmethod
    async def save(self, entity: FinTop10FloatHolder) -> FinTop10FloatHolder: ...
    @abstractmethod
    async def save_batch(self, entities: list[FinTop10FloatHolder]) -> int: ...
    @abstractmethod
    async def find_by_symbol(
        self, symbol: str, end_date: Optional[date] = None
    ) -> list[FinTop10FloatHolder]: ...
