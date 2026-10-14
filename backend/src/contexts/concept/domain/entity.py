"""概念实体 — 概念聚合根

配套设计文档：
  docs/dev/06gainian/01-domain-design.md §2
  docs/dev/step2/02datamanage/04-概念数据adata同源改造方案.md §4
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class ConceptSource(str, Enum):
    """概念数据来源（adata 采集，同花顺数据）"""
    THS = "ths"


class ConceptType(str, Enum):
    """概念类型（粗粒度分类）"""
    INDUSTRY = "industry"   # 行业概念（接近 SW 行业）
    THEME = "theme"         # 主题概念（如"碳中和"）
    STYLE = "style"         # 风格概念（如"高股息"）
    REGION = "region"       # 地域概念（如"雄安"）
    EVENT = "event"         # 事件概念（如"中字头"）
    OTHER = "other"


@dataclass(frozen=False)
class Concept:
    """概念实体（聚合根）

    不变式：
    - index_code（同花顺指数编码 885xxx）全局唯一，是业务键；name 可能变更
    - is_active = False 时仍保留历史（软删除）
    """

    id: Optional[int] = field(default=None)
    index_code: str = field(default="")
    concept_code: Optional[str] = field(default=None)
    name: str = field(default="")
    source: ConceptSource = field(default=ConceptSource.THS)
    concept_type: ConceptType = field(default=ConceptType.OTHER)
    description: Optional[str] = field(default=None)
    stock_count: int = field(default=0)
    is_active: bool = field(default=True)
    first_seen_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_synced_at: Optional[datetime] = field(default=None)


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


class ConceptNotFoundError(Exception):
    """指定概念不存在（按 id / name 查不到）"""

    message: str

    def __init__(self, *, id: int | None = None, name: str | None = None):
        if id is not None:
            self.message = f"概念 id={id} 不存在"
        elif name is not None:
            self.message = f"概念 name={name!r} 不存在"
        else:
            self.message = "概念不存在"
        super().__init__(self.message)
