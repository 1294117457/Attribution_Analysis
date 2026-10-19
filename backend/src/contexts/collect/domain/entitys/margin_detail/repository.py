"""MarginDetailRepository Protocol"""
from __future__ import annotations

from typing import Protocol



class MarginDetailRepository(Protocol):
    async def save(self, bos: list[object]) -> int: ...


__all__ = ["MarginDetailRepository"]
