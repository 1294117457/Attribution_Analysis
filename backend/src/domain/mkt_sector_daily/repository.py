"""mkt_sector_daily — 仓储接口"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from domain.mkt_sector_daily.entity import MktSectorDaily


class MktSectorDailyRepository(ABC):
    @abstractmethod
    async def save(self, entity: MktSectorDaily) -> MktSectorDaily: ...
    @abstractmethod
    async def save_batch(self, entities: list[MktSectorDaily]) -> int: ...
    @abstractmethod
    async def find_by_date(
        self, trade_date: date, sector_type: Optional[str] = None
    ) -> list[MktSectorDaily]: ...
    @abstractmethod
    async def find_by_sector(
        self,
        sector_type: str,
        sector_code: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[MktSectorDaily]: ...
