"""FinReportRepository Protocol"""
from __future__ import annotations

from typing import Protocol



class FinReportRepository(Protocol):
    async def save(self, bos: list[object]) -> int: ...


__all__ = ["FinReportRepository"]
