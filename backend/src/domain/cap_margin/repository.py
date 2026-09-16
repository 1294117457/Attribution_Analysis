"""cap_margin — 仓储接口"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from domain.cap_margin.entity import CapMargin


class CapMarginRepository(ABC):
    @abstractmethod
    async def save(self, entity: CapMargin) -> CapMargin: ...
    @abstractmethod
    async def save_batch(self, entities: list[CapMargin]) -> int: ...
    @abstractmethod
    async def find_by_date(
        self, trade_date: date, exchange_id: Optional[str] = None
    ) -> list[CapMargin]: ...
