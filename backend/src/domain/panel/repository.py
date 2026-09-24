"""StockPanel 组合查询 — 领域层 Protocol

设计原则：
- 严格只服务于"列表 + 多表快照"场景，不承担单表的 CRUD
- 跨表 JOIN 是它的本职，不算越界
- list_membership_by_symbols 合并到此仓储，避免服务层跨仓储编排

应用层通过 Protocol 注入依赖，Infrastructure 层提供具体实现。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Protocol, runtime_checkable

from domain.panel.value_objects import StockPanelRow

if TYPE_CHECKING:
    from domain.concept.value_objects import ConceptBriefVO
    from application.dto.pool import PoolMembershipVO


@runtime_checkable
class StockPanelComposeRepository(Protocol):
    """列表面板专用组合仓储"""

    async def list_paginated(
        self,
        q: Optional[str] = None,
        industry: Optional[str] = None,
        market: Optional[str] = None,
        exchange: Optional[str] = None,
        is_hs: Optional[str] = None,
        list_status: Optional[str] = None,
        exclude_st: Optional[bool] = None,
        min_total_mv: Optional[float] = None,
        with_pools: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[StockPanelRow], int]:
        """分页 + 多维筛选 + 4 表快照，返回 (rows, total)

        with_pools 当前在此方法签名上保留以保持向后兼容的接口形状；
        实际批量反查由调用方调用 list_membership_by_symbols 触发。
        """
        ...

    async def list_membership_by_symbols(
        self, symbols: list[str]
    ) -> dict[str, list["PoolMembershipVO"]]:
        """批量反向查询池成员关系

        返回 dict[symbol, list[PoolMembershipVO]]。
        未出现在 dict key 中的 symbol 表示未加入任何池。
        仅返回未归档池（is_archived=False）。

        性能：单次 SQL，symbol IN (:symbols) 命中
        ix_stock_pool_members_symbol 索引，symbols 数量上限 ≤ page_size（500）。
        """
        ...

    async def list_concepts_by_symbols(
        self, symbols: list[str]
    ) -> dict[str, list["ConceptBriefVO"]]:
        """批量反向查询概念成员关系

        返回 dict[symbol, list[ConceptBriefVO]]。
        未出现在 dict key 中的 symbol 表示无活跃概念。
        由调用方（StockPanelAppService）注入 ConceptRepository 实现，
        本 Protocol 仅声明签名。
        """
        ...