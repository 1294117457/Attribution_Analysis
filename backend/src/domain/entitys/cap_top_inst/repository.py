"""cap_top_inst — 仓储接口"""

from abc import ABC, abstractmethod

from domain.entitys.cap_top_inst.entity import CapTopInst


class CapTopInstRepository(ABC):
    """龙虎榜机构明细仓储（主键 trade_date + symbol + exalter）"""

    @abstractmethod
    async def save_batch(self, entities: list[CapTopInst]) -> int: ...

    @abstractmethod
    async def find_by_date_symbol(
        self,
        trade_date,
        symbol: str,
    ) -> list[CapTopInst]: ...
