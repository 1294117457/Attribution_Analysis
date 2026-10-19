"""FinTop10HoldersRepository Protocol"""
from __future__ import annotations

from typing import Protocol



class FinTop10HoldersRepository(Protocol):
    async def save(self, bos: list[object]) -> int: ...


__all__ = ["FinTop10HoldersRepository"]
