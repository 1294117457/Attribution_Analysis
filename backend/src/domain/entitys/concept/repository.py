"""Concept 仓储协议（读侧）

写侧（清单 upsert、成分股替换、日 K）只被采集任务使用，
直接调用 infrastructure 的 ConceptRepoImpl，不在领域协议中暴露。

配套设计文档：
  docs/dev/06gainian/01-domain-design.md §5
  docs/dev/step2/02datamanage/04-概念数据adata同源改造方案.md §5.3
"""

from __future__ import annotations

from datetime import date, datetime
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

    async def get_concept_by_index_code(self, index_code: str) -> Optional[Concept]:
        """按 index_code 查概念（用于概念 K 线 meta 注入）"""
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

    # ── 日 K 收盘（实时行情降级用）─────────────
    async def get_latest_closes(self, index_codes: list[str]) -> dict[str, dict]:
        """每个概念最近一条日 K：{index_code: {concept_name, trade_date, close, change, change_pct}}"""
        ...

    # ════════════════════════════════════════════════════════════════
    #  概念大盘 v2（01 概念大盘页 · 纯追加）
    # ════════════════════════════════════════════════════════════════

    async def list_board_rows(
        self,
        type_filter: Optional[str] = None,
        sort_by: str = "pct_change",
        order: str = "desc",
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list, int]:
        """概念大盘分页（不带实时行情，行情由 service 经实时接口补）

        v2 矫正：返回 list of 私有 row 类（由仓储实现层定义）+ total。
        协议层用 list 泛型占位，避免泄漏到 domain。
        """
        ...

    async def list_members_by_concept(
        self,
        concept_id: int,
        sort_by: str = "pct_change",
        order: str = "desc",
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict], int]:
        """单概念成分股（join stock_infos + fin_daily_basics 最新一行）

        v2 矫正：返回 list[dict]（与现有 list_members 风格一致），
        路由层组装为 ConceptMemberItemVO。
        """
        ...

    async def list_membership_by_symbols(
        self, symbols: list[str]
    ) -> dict[str, list[dict]]:
        """批量查询股票所属池（避免 N+1）—— 用于概念成分股页 with_pools=True

        返回 dict[symbol, [{pool_id, name, pool_type, joined_at}, ...]]
        """
        ...

    # ════════════════════════════════════════════════════════════════
    #  概念 K 线（用于概念大盘 · 概念抽屉头部 K 线图）
    # ════════════════════════════════════════════════════════════════

    async def list_concept_kline(
        self,
        index_code: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 250,
    ) -> list[dict]:
        """概念指数日 K（concept_index_ths），按日期升序

        返回 list[{date(YYYY-MM-DD), open, high, low, close, volume, amount, change_pct}]。
        """
        ...
