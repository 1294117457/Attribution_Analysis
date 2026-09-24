"""Concept 仓储协议

配套设计文档：
  docs/dev/06gainian/01-domain-design.md §5
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol, runtime_checkable

from domain.concept.entity import Concept, ConceptMember
from domain.concept.value_objects import ConceptBriefVO, ConceptGroupedVO


@runtime_checkable
class ConceptRepository(Protocol):
    """概念聚合根仓储协议

    职责：
    - 写入：采集器写入
    - 读取：列表 / 详情 / 反查
    - 软删除：标记 is_active = False
    """

    # ── 写入 ─────────────────────────────────────
    async def upsert_concept(self, concept: Concept) -> Concept:
        """新增或更新概念，返回带 id 的 Concept

        - 命中 (name, source) 唯一约束 → 更新 description / concept_type / is_active
        - 未命中 → INSERT
        """
        ...

    async def upsert_members(
        self,
        concept_id: int,
        members: list[ConceptMember],
    ) -> int:
        """批量写入概念成员，先 DELETE 旧再 INSERT 新，返回写入条数

        全量覆盖语义：保证 stock_concept_members 与采集数据一致。
        """
        ...

    # ── 单条读取 ──────────────────────────────────
    async def get_concept_by_id(self, concept_id: int) -> Optional[Concept]:
        ...

    async def get_concept_by_name(
        self, name: str, source: str = "em"
    ) -> Optional[Concept]:
        ...

    # ── 反向查询（核心：被 panel 复用）─────────────
    async def list_concepts_by_symbol(self, symbol: str) -> list[ConceptBriefVO]:
        """单只股票所属的所有活跃概念"""
        ...

    async def list_concepts_by_symbols(
        self, symbols: list[str]
    ) -> dict[str, list[ConceptBriefVO]]:
        """批量反向查询，避免 N+1

        单次 SQL：symbol IN (:symbols) + JOIN concepts
        返回 dict[symbol, list[ConceptBriefVO]]，
        未在结果中的 symbol 表示无活跃概念（不会自动补 key）。
        """
        ...

    async def list_concepts_by_symbol_grouped(
        self, symbol: str
    ) -> list[ConceptGroupedVO]:
        """单只股票所属的所有活跃概念（含 concept_type / description，用于详情抽屉「概念」Tab）

        与 list_concepts_by_symbol 的区别：
        - list_concepts_by_symbol：返回 ConceptBriefVO[]（3 字段），用于列表预热
        - list_concepts_by_symbol_grouped：返回 ConceptGroupedVO[]（5 字段），用于抽屉 Tab 渲染
        """
        ...

    # ── 列表 / 统计 ──────────────────────────────
    async def list_concepts(
        self,
        q: Optional[str] = None,
        source: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Concept], int]:
        """分页列出概念"""
        ...

    async def count_concepts(
        self,
        source: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        ...

    # ── 同步状态 ──────────────────────────────────
    async def get_last_synced_at(self, source: str = "em") -> Optional[datetime]:
        """最近一次同步时间（取 is_active 概念中最大的 last_synced_at）"""
        ...
