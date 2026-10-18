"""概念成员实体（子实体）

配套设计文档：
  docs/dev/06gainian/01-domain-design.md §2
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class ConceptSource(str, Enum):
    """概念数据来源（adata 采集，同花顺数据）"""
    THS = "ths"


@dataclass(frozen=True)
class ConceptMember:
    """概念成员（子实体）

    不变式：(symbol, concept_id) 联合唯一；reason 是"该股票为什么属于该概念"
    """

    symbol: str
    concept_id: int
    source: ConceptSource = ConceptSource.THS
    reason: Optional[str] = None
    joined_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
