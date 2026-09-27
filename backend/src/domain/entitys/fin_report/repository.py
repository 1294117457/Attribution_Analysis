"""fin_report — 仓储接口"""

from abc import ABC, abstractmethod
from typing import Optional
from datetime import date

from domain.entitys.fin_report.entity import FinReport


class FinReportRepository(ABC):
    """财报仓储（主键 symbol + end_date + report_type）"""

    @abstractmethod
    async def save(self, entity: FinReport) -> FinReport: ...

    @abstractmethod
    async def save_batch(self, entities: list[FinReport]) -> int: ...

    @abstractmethod
    async def find_by_symbol(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[FinReport]: ...
