"""cap_moneyflow — 仓储接口"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from domain.cap_moneyflow.entity import CapMoneyflow


class CapMoneyflowRepository(ABC):
    """个股资金流向仓储接口"""

    @abstractmethod
    async def save(self, entity: CapMoneyflow) -> CapMoneyflow: ...

    @abstractmethod
    async def save_batch(self, entities: list[CapMoneyflow]) -> int: ...

    @abstractmethod
    async def find_by_symbol_date(
        self, symbol: str, trade_date: date
    ) -> Optional[CapMoneyflow]: ...

    @abstractmethod
    async def find_by_symbol(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[CapMoneyflow]: ...
