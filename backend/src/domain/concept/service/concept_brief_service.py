"""概念摘要领域服务 — 纯业务规则（无 IO）

负责"概念摘要"的业务规则（不属于任何单一 entity）：
- 按 concept_type 业务优先级排序
- 取 top_k 构造主视图
- 计算 overflow 数量
- 注入板块快照（涨幅、颜色等）

DDD.md §1 service 条目：
- 只依赖 domain（entity / VO），不依赖任何外部 SDK
- 不调 HTTP、不发 MQ、不取系统时钟
- 通常没有副作用（无 IO、无状态变更）
- 可独立单测
"""
from __future__ import annotations

from typing import Optional

from domain.concept.value_objects import (
    CONCEPT_TYPE_PRIORITY,
    ConceptBriefVO,
    ConceptMainVO,
)


DEFAULT_TOP_K = 3


class ConceptBriefService:
    """概念摘要领域服务

    业务规则：
    1. 按 concept_type 业务优先级排序（industry > theme > event > style > region > other）
    2. 同 type 内按 name 字典序
    3. 取 top_k 构造 ConceptMainVO
    4. 计算 overflow = max(0, 总数 - top_k)
    """

    def __init__(self, top_k: int = DEFAULT_TOP_K) -> None:
        self._top_k = top_k

    def build_main_concepts(
        self,
        concept_map: dict[str, list[ConceptBriefVO]],
        snapshot_map: Optional[dict[str, dict]] = None,
        top_k: Optional[int] = None,
    ) -> dict[str, tuple[list[ConceptMainVO], int]]:
        """对每只股票的 ConceptBriefVO[] 排序并取 top_k，构造 ConceptMainVO 视图。

        Args:
            concept_map: {symbol: [ConceptBriefVO, ...]}
            snapshot_map: {concept_name: {pct_change, color, ...}}
            top_k: 主视图展示上限（默认 self._top_k）

        Returns:
            {symbol: (main_concepts, overflow_count)}
        """
        k = top_k if top_k is not None else self._top_k
        snapshot_map = snapshot_map or {}
        out: dict[str, tuple[list[ConceptMainVO], int]] = {}
        for symbol, briefs in concept_map.items():
            if not briefs:
                out[symbol] = ([], 0)
                continue

            sorted_briefs = sorted(
                briefs,
                key=lambda b: (
                    CONCEPT_TYPE_PRIORITY.get(b.concept_type, 99),
                    b.name,
                ),
            )
            top = sorted_briefs[:k]
            main_vos = [
                ConceptMainVO.from_brief(
                    brief=b,
                    display_order=idx + 1,
                    snapshot=snapshot_map.get(b.name) or None,
                )
                for idx, b in enumerate(top)
            ]
            overflow = max(0, len(briefs) - k)
            out[symbol] = (main_vos, overflow)
        return out
