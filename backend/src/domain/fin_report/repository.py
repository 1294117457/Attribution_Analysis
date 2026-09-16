"""fin_report — 仓储接口"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from domain.fin_report.entity import FinReport


class FinReportRepository(ABC):
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
        report_type: Optional[str] = None,
    ) -> list[FinReport]: ...
