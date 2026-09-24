"""概念实体 — 概念聚合根

配套设计文档：
  docs/dev/06gainian/01-domain-design.md §2
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class ConceptSource(str, Enum):
    """概念数据来源"""
    EM = "em"      # 东方财富（默认）
    THS = "ths"    # 同花顺


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
    - name 与 source 联合唯一
    - is_active = False 时仍保留历史（软删除）
    - last_synced_at 必填（标记采集状态）
    """

    id: Optional[int] = field(default=None)
    name: str = field(default="")
    source: ConceptSource = field(default=ConceptSource.EM)
    concept_type: ConceptType = field(default=ConceptType.OTHER)
    description: Optional[str] = field(default=None)
    stock_count: int = field(default=0)
    is_active: bool = field(default=True)
    first_seen_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_synced_at: Optional[datetime] = field(default=None)

    @classmethod
    def create(
        cls,
        name: str,
        source: ConceptSource = ConceptSource.EM,
        concept_type: ConceptType = ConceptType.OTHER,
        description: Optional[str] = None,
    ) -> "Concept":
        """工厂方法：从 BO 创建"""
        if not name or not name.strip():
            raise ValueError(f"Concept name 不能为空: {name!r}")
        return cls(
            name=name.strip(),
            source=source,
            concept_type=concept_type,
            description=description,
        )

    def mark_synced(
        self,
        member_count: int,
        at: Optional[datetime] = None,
    ) -> None:
        """同步完成后调用：更新 last_synced_at 和 stock_count"""
        self.last_synced_at = at or datetime.now(timezone.utc)
        self.stock_count = member_count
        if not self.is_active:
            # 重新激活（曾下线又出现）
            self.is_active = True

    def deactivate(self) -> None:
        """软删除：标记为不活跃，保留历史"""
        self.is_active = False


@dataclass(frozen=True)
class ConceptMember:
    """概念成员（子实体）

    不变式：
    - (symbol, concept_id) 联合唯一
    - source 必须与所属 Concept.source 一致
    """

    symbol: str
    concept_id: int
    source: ConceptSource
    joined_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @classmethod
    def create(
        cls,
        symbol: str,
        concept_id: int,
        source: ConceptSource,
        joined_at: Optional[datetime] = None,
    ) -> "ConceptMember":
        if not symbol or len(symbol) != 6 or not symbol.isdigit():
            raise ValueError(f"无效的 symbol: {symbol!r}")
        return cls(
            symbol=symbol,
            concept_id=concept_id,
            source=source,
            joined_at=joined_at or datetime.now(timezone.utc),
        )
