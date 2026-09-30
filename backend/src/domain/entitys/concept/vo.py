"""概念只读投影 VO

配套设计文档：
  docs/dev/06gainian/01-domain-design.md §4
  docs/dev/08concept/02-class-design.md  (08concept 二期增量)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════════
#  06gainian 既有 VO（08concept 扩展了 concept_type 字段）
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ConceptBriefVO:
    """概念简略 VO（用于嵌入到 StockPanelItemVO.concepts）

    设计为 frozen dataclass：
    - 不可变，避免下游误改
    - hashable，可放进 set / 作为 dict key
    - 字段最小化（前端展示需要的字段）

    08concept 增量：
    - 新增 `concept_type` 字段（带默认值 "other"），用于主概念列排序和前端染色
    - 向后兼容：旧代码 / 旧响应忽略此字段也无影响
    """

    concept_id: int
    name: str
    source: str  # ConceptSource 的 value（"ths"），方便序列化
    concept_type: str = "other"  # 08concept 新增：industry/theme/style/region/event/other


@dataclass(frozen=True)
class ConceptGroupedVO:
    """概念分组 VO（用于详情抽屉「概念」Tab）

    与 ConceptBriefVO 的区别：
    - ConceptBriefVO：4 字段，用于列表预热 + 主概念排序
    - ConceptGroupedVO：多了 description / reason，用于抽屉 Tab 分组展示
    """

    concept_id: int
    name: str
    source: str  # "ths"
    concept_type: str  # industry / theme / style / region / event / other
    description: Optional[str] = None
    reason: Optional[str] = None  # 该股票的入选理由（stock_concept_members.reason）
    index_code: Optional[str] = None  # 同花顺指数编码，实时行情按它查询


# ═══════════════════════════════════════════════════════════════════════════════
#  08concept 新增 VO
# ═══════════════════════════════════════════════════════════════════════════════


# 概念类型显示优先级（数值越小越靠前）
# 用于 StockInfoList 行内"主概念"列的业务排序
CONCEPT_TYPE_PRIORITY: dict[str, int] = {
    "industry": 1,  # 行业概念 — 最高优先
    "theme":    2,  # 主题概念
    "event":    3,  # 事件概念
    "style":    4,  # 风格概念
    "region":   5,  # 地域概念
    "other":    6,  # 其他概念
}


@dataclass(frozen=True)
class ConceptMainVO:
    """主概念视图（列表行渲染专用，08concept 增量）

    与 ConceptBriefVO 的区别：
    - ConceptBriefVO：通用简略视图（4 字段，无业务排序）
    - ConceptMainVO：业务排序视图（5 字段，多 display_order）

    字段：
    - display_order: 1=最优先（industry），越大越靠后；前端按 order 升序渲染
    - snapshot: 09concept 新增 行情快照 dict（{pct_change, color, ...} 或 None）
    """

    concept_id: int
    name: str
    source: str
    concept_type: str
    display_order: int
    snapshot: Optional[dict] = None  # 09concept: 板块涨幅快照（None 表示无快照数据）

    @classmethod
    def from_brief(
        cls,
        brief: ConceptBriefVO,
        display_order: int,
        snapshot: Optional[dict] = None,
    ) -> "ConceptMainVO":
        """从 ConceptBriefVO 构造（保留所有字段）"""
        return cls(
            concept_id=brief.concept_id,
            name=brief.name,
            source=brief.source,
            concept_type=brief.concept_type,
            display_order=display_order,
            snapshot=snapshot,
        )
