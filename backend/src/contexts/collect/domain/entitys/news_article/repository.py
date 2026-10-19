"""NewsArticleRepository Protocol

fetcher 返回 list[dict]，service 内 dict → row
"""
from __future__ import annotations

from typing import Protocol


class NewsArticleRepository(Protocol):
    async def save_dicts(self, items: list[dict]) -> int: ...


__all__ = ["NewsArticleRepository"]
