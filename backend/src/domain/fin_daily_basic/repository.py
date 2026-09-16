"""fin_daily_basic — 仓储接口"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from domain.fin_daily_basic.entity import FinDailyBasic


class FinDailyBasicRepository(ABC):
    @abstractmethod
    async def save(self, entity: FinDailyBasic) -> FinDailyBasic: ...
    @abstractmethod
    async def save_batch(self, entities: list[FinDailyBasic]) -> int: ...
    @abstractmethod
    async def find_by_symbol(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[FinDailyBasic]: ...
