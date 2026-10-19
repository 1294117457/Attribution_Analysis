"""MoneyflowHsgtRepository Protocol"""
from __future__ import annotations

from typing import Protocol



class MoneyflowHsgtRepository(Protocol):
    async def save(self, bos: list[object]) -> int: ...


__all__ = ["MoneyflowHsgtRepository"]
