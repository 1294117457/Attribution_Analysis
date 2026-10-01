# TODO: DDD 仓储接口已定义，待 infrastructure 层实现对应 *_repo_impl
"""mkt_sector_daily — 仓储接口"""

from abc import ABC, abstractmethod
from datetime import date

from domain.entitys.mkt_sector_daily.entity import MktSectorDaily


class MktSectorDailyRepository(ABC):
    """板块行情日线仓储（主键 sector_type + sector_code + trade_date）"""

    @abstractmethod
    async def save(self, entity: MktSectorDaily) -> MktSectorDaily: ...

    @abstractmethod
    async def save_batch(self, entities: list[MktSectorDaily]) -> int: ...

    @abstractmethod
    async def find_by_date(
        self,
        trade_date: date,
        sector_type: str | None = None,
    ) -> list[MktSectorDaily]: ...

    @abstractmethod
    async def find_by_sector(
        self,
        sector_type: str,
        sector_code: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[MktSectorDaily]: ...
