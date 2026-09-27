"""cap_margin — 仓储接口"""

from abc import ABC, abstractmethod
from typing import Optional
from datetime import date

from domain.entitys.cap_margin.entity import CapMargin


class CapMarginRepository(ABC):
    """两融汇总仓储（主键 exchange_id + trade_date，按交易所维度）"""

    @abstractmethod
    async def save(self, entity: CapMargin) -> CapMargin: ...

    @abstractmethod
    async def save_batch(self, entities: list[CapMargin]) -> int: ...

    @abstractmethod
    async def find_by_date(
        self,
        trade_date: date,
        exchange_id: Optional[str] = None,
    ) -> list[CapMargin]: ...
