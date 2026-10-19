"""ConceptRepository Protocol"""
from __future__ import annotations

from typing import Optional, Protocol



class ConceptRepository(Protocol):
    """概念清单仓储协议"""

    async def save(self, bos: list[object]) -> int: ...
    async def list_all_codes(self) -> list[str]: ...
    async def get_id_by_name(self, name: str) -> Optional[int]: ...


__all__ = ["ConceptRepository"]
