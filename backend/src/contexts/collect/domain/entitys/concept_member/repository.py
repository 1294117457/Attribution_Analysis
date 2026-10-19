"""ConceptMemberRepository Protocol"""
from __future__ import annotations

from typing import Protocol



class ConceptMemberRepository(Protocol):
    async def save_by_concept(
        self, concept_id: int, bos: list[object],
    ) -> int: ...


__all__ = ["ConceptMemberRepository"]
