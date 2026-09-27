"""mkt_market_daily — 仓储接口"""

from abc import ABC, abstractmethod
from datetime import date

from domain.entitys.mkt_market_daily.entity import MktMarketDaily


class MktMarketDailyRepository(ABC):
    """市场行情日线仓储（主键 market + trade_date）"""

    @abstractmethod
    async def save(self, entity: MktMarketDaily) -> MktMarketDaily: ...

    @abstractmethod
    async def save_batch(self, entities: list[MktMarketDaily]) -> int: ...

    @abstractmethod
    async def find_by_market(
        self,
        market: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[MktMarketDaily]: ...
