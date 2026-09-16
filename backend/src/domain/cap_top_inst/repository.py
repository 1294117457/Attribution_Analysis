"""cap_top_inst — 仓储接口"""

from abc import ABC, abstractmethod
from datetime import date

from domain.cap_top_inst.entity import CapTopInst


class CapTopInstRepository(ABC):
    @abstractmethod
    async def save_batch(self, entities: list[CapTopInst]) -> int: ...
    @abstractmethod
    async def find_by_date_symbol(
        self, trade_date: date, symbol: str
    ) -> list[CapTopInst]: ...
