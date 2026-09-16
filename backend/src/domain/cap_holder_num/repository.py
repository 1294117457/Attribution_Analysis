"""cap_holder_num — 仓储接口"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from domain.cap_holder_num.entity import CapHolderNum


class CapHolderNumRepository(ABC):
    @abstractmethod
    async def save(self, entity: CapHolderNum) -> CapHolderNum: ...
    @abstractmethod
    async def save_batch(self, entities: list[CapHolderNum]) -> int: ...
    @abstractmethod
    async def find_by_symbol(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[CapHolderNum]: ...
