"""HsgtTop10Repository Protocol"""
from __future__ import annotations

from typing import Protocol



class HsgtTop10Repository(Protocol):
    async def save(self, bos: list[object]) -> int: ...


__all__ = ["HsgtTop10Repository"]
