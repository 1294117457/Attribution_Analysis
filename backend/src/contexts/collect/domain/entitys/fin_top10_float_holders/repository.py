"""FinTop10FloatHoldersRepository Protocol"""
from __future__ import annotations

from typing import Protocol



class FinTop10FloatHoldersRepository(Protocol):
    async def save(self, bos: list[object]) -> int: ...


__all__ = ["FinTop10FloatHoldersRepository"]
