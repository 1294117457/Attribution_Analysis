"""mkt_market_daily — 仓储接口"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from domain.mkt_market_daily.entity import MktMarketDaily


class MktMarketDailyRepository(ABC):
    @abstractmethod
    async def save(self, entity: MktMarketDaily) -> MktMarketDaily: ...
    @abstractmethod
    async def save_batch(self, entities: list[MktMarketDaily]) -> int: ...
    @abstractmethod
    async def find_by_market(
        self,
        market: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[MktMarketDaily]: ...
