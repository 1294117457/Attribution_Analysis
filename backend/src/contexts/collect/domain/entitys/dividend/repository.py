"""DividendRepository Protocol"""
from __future__ import annotations

from typing import Protocol



class DividendRepository(Protocol):
    async def save(self, bos: list[object]) -> int: ...


__all__ = ["DividendRepository"]
