"""Concept 仓储协议（读侧）

写侧（清单 upsert、成分股替换、入选理由、日 K、快照）只被采集任务使用，
直接调用 infrastructure 的 ConceptRepoImpl，不在领域协议中暴露。

配套设计文档：
  docs/dev/06gainian/01-domain-design.md §5
  docs/dev/step2/02datamanage/04-概念数据adata同源改造方案.md §5.3
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol, runtime_checkable

from domain.entitys.concept.entity import Concept
from domain.entitys.concept.vo import ConceptBriefVO, ConceptGroupedVO


@runtime_checkable
class ConceptRepository(Protocol):
    """概念聚合根仓储协议"""

    # ── 单条读取 ──────────────────────────────────
    async def get_concept_by_id(self, concept_id: int) -> Optional[Concept]:
        ...

    async def get_concept_by_name(self, name: str) -> Optional[Concept]:
        ...

    async def list_members(self, concept_id: int) -> list[dict]:
        """概念成分股：[{symbol, name, reason}]，name 来自 stock_infos"""
        ...

    # ── 反向查询（核心：被 panel 复用）─────────────
    async def list_concepts_by_symbol(self, symbol: str) -> list[ConceptBriefVO]:
        """单只股票所属的所有活跃概念"""
        ...

    async def list_concepts_by_symbols(
        self, symbols: list[str]
    ) -> dict[str, list[ConceptBriefVO]]:
        """批量反向查询，避免 N+1；返回 dict[symbol, list[ConceptBriefVO]]"""
        ...

    async def list_concepts_by_symbol_grouped(
        self, symbol: str
    ) -> list[ConceptGroupedVO]:
        """单只股票所属的所有活跃概念（含 concept_type / reason，用于详情抽屉「概念」Tab）"""
        ...

    # ── 列表 / 统计 ──────────────────────────────
    async def list_concepts(
        self,
        q: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Concept], int]:
        """分页列出概念"""
        ...

    async def count_concepts(self, is_active: Optional[bool] = None) -> int:
        ...

    async def get_last_synced_at(self) -> Optional[datetime]:
        """成分股最近一次同步时间（concepts.last_synced_at 最大值）"""
        ...

    # ── 概念快照 ───────────────────────
    async def list_snapshots_for_names(
        self, names: list[str]
    ) -> dict[str, dict]:
        """批量取多个概念的"最新一条"快照；返回 dict[concept_name, snapshot_dict]"""
        ...
