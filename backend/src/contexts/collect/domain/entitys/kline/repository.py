"""KlineRepository Protocol（domain 层定义）

infrastructure.persistence.repositories.kline_repo.KlineRepository 实现此 Protocol。
"""
from __future__ import annotations

from datetime import date
from typing import Iterable, Protocol

from contexts.market.domain.entities.kline.entity import Kline


class KlineRepository(Protocol):
    """日 K 线仓储协议"""

    async def save_klines(self, klines: list[Kline]) -> int: ...
    async def find(
        self, symbol: str, start: date | None, end: date | None,
    ) -> list[Kline]: ...
    async def find_by_symbol(
        self, symbol, start_date=None, end_date=None, limit: int = 1000,
        order_desc: bool = False,
    ) -> list[Kline]: ...
    async def count_by_symbol(self, symbol) -> int: ...
    async def get_coverage(
        self, symbols: Iterable[str],
    ) -> dict[str, tuple[date, date]]: ...


__all__ = ["KlineRepository"]
