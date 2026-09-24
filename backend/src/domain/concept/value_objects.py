"""概念只读投影 VO

配套设计文档：
  docs/dev/06gainian/01-domain-design.md §4
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ConceptBriefVO:
    """概念简略 VO（用于嵌入到 StockPanelItemVO.concepts）

    设计为 frozen dataclass：
    - 不可变，避免下游误改
    - hashable，可放进 set / 作为 dict key
    - 字段最小化（仅前端展示需要的 3 个字段）
    """

    concept_id: int
    name: str
    source: str  # ConceptSource 的 value（"em" / "ths"），方便序列化


@dataclass(frozen=True)
class ConceptGroupedVO:
    """概念分组 VO（用于详情抽屉「概念」Tab）

    与 ConceptBriefVO 的区别：
    - ConceptBriefVO：3 字段，用于列表预热
    - ConceptGroupedVO：5 字段（多了 concept_type、description），用于抽屉 Tab 分组展示
    """

    concept_id: int
    name: str
    source: str  # "em" / "ths"
    concept_type: str  # industry / theme / style / region / event / other
    description: Optional[str] = None
