"""StockInfoRepository Protocol（domain 层定义）"""
from __future__ import annotations

from datetime import date
from typing import Iterable, Protocol


class StockInfoRepository(Protocol):
    """股票基本信息仓储协议"""

    async def save_batch(self, rows: list[dict]) -> int: ...
    async def find(self, symbol: str) -> dict | None: ...
    async def list_symbols(self, list_status: str = "L") -> list[str]: ...
    async def list_dates(
        self, symbols: Iterable[str],
    ) -> dict[str, date | None]: ...


__all__ = ["StockInfoRepository"]
