"""cap_top_list — 仓储接口"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from domain.cap_top_list.entity import CapTopList


class CapTopListRepository(ABC):
    @abstractmethod
    async def save(self, entity: CapTopList) -> CapTopList: ...
    @abstractmethod
    async def save_batch(self, entities: list[CapTopList]) -> int: ...
    @abstractmethod
    async def find_by_date(
        self, trade_date: date, symbol: Optional[str] = None
    ) -> list[CapTopList]: ...
    @abstractmethod
    async def find_by_symbol(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[CapTopList]: ...
