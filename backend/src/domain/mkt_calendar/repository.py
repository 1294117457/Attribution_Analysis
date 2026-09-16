"""mkt_calendar — 仓储接口"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from domain.mkt_calendar.entity import MktCalendar


class MktCalendarRepository(ABC):
    @abstractmethod
    async def save(self, entity: MktCalendar) -> MktCalendar: ...
    @abstractmethod
    async def save_batch(self, entities: list[MktCalendar]) -> int: ...
    @abstractmethod
    async def find_by_range(
        self,
        exchange: str,
        start_date: date,
        end_date: date,
        is_open: Optional[bool] = None,
    ) -> list[MktCalendar]: ...
