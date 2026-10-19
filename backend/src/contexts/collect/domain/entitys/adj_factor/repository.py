"""AdjFactorRepository Protocol（domain 层定义）"""
from __future__ import annotations

from typing import Protocol



class AdjFactorRepository(Protocol):
    """复权因子仓储协议"""

    async def save(self, bos: list[object]) -> int: ...


__all__ = ["AdjFactorRepository"]
