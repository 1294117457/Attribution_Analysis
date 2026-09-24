"""StockPanel 应用服务

职责单一：把"分页 + 多表快照 + 批量池"组合查询的结果组装为分页 VO。
不做单表 CRUD，不做领域事件，不依赖其他应用服务。

对应路由：GET /api/v1/stock-panel/
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from application.concept_service import ConceptAppService
from application.dto.panel import (
    StockPanelItemVO,
    StockPanelListVO,
    StockPanelQueryRequest,
)
from application.dto.pool import PoolMembershipVO
from domain.concept.value_objects import ConceptBriefVO
from domain.panel.repository import StockPanelComposeRepository
from domain.panel.value_objects import StockPanelRow
from infrastructure.collectors.registry import get_registry
from infrastructure.collectors.protocols import ConceptFetcher
from infrastructure.repositories.concept_repository import ConceptRepoImpl
from infrastructure.repositories.panel_compose_repository import (
    StockPanelComposeRepoImpl,
)


class StockPanelAppService:
    """列表面板应用服务"""

    def __init__(
        self,
        session: AsyncSession,
        concept_app_service: Optional[ConceptAppService] = None,
    ):
        self._session = session

        # 概念服务：用于注入 ConceptRepository 到 panel 仓储
        # （仅当 Fetcher 已注册时才可构造）
        self._concept_app = concept_app_service
        concept_repo = None
        if concept_app_service is not None:
            # 由 concept_app_service 内部持有 repo，可借用其 session
            # 简化：通过同一 session 构造一个新 ConceptRepoImpl 即可
            concept_repo = ConceptRepoImpl(session)

        self._repo: StockPanelComposeRepository = StockPanelComposeRepoImpl(
            session,
            concept_repo=concept_repo,
        )

    async def query_panels(
        self, req: StockPanelQueryRequest
    ) -> StockPanelListVO:
        """分页 + 多维筛选 + 4 表快照 + 池信息 + 概念（with_pools/with_concepts=True 时填充）

        SQL 数量：最多 3 条
        - 1× 主查询（4 表 LEFT JOIN + 子查询）
        - 1× 批量反查池（symbol IN (:symbols)，仅 with_pools=True 时）
        - 1× 批量反查概念（symbol IN (:symbols)，仅 with_concepts=True 时）
        """
        rows, total = await self._repo.list_paginated(
            q=req.q,
            industry=req.industry,
            market=req.market,
            exchange=req.exchange,
            is_hs=req.is_hs,
            list_status=req.list_status,
            exclude_st=req.exclude_st,
            min_total_mv=req.min_total_mv,
            with_pools=req.with_pools,
            page=req.page,
            page_size=req.page_size,
        )

        symbols = [r.symbol for r in rows]

        # with_pools 时一次性批量反查池（最多 1 次额外 SQL）
        pool_map: dict[str, list[PoolMembershipVO]] = {}
        if req.with_pools and rows:
            pool_map = await self._repo.list_membership_by_symbols(symbols)

        # with_concepts 时一次性批量反查概念（最多 1 次额外 SQL）
        concept_map: dict[str, list[ConceptBriefVO]] = {}
        if req.with_concepts and rows and self._concept_app is not None:
            concept_map = await self._repo.list_concepts_by_symbols(symbols)

        items = [
            _to_vo(r, pool_map.get(r.symbol, []), concept_map.get(r.symbol, []))
            for r in rows
        ]
        return StockPanelListVO.from_list(items, total, req.page, req.page_size)


def _to_vo(
    r: StockPanelRow,
    pools: list[PoolMembershipVO],
    concepts: list[ConceptBriefVO],
) -> StockPanelItemVO:
    """StockPanelRow → StockPanelItemVO（字段 1:1 + pools/concepts 注入）"""
    return StockPanelItemVO(
        symbol=r.symbol,
        ts_code=r.ts_code,
        name=r.name,
        area=r.area,
        industry=r.industry,
        market=r.market,
        exchange=r.exchange,
        list_date=r.list_date,
        list_status=r.list_status,
        is_hs=r.is_hs,
        act_name=r.act_name,
        act_ent_type=r.act_ent_type,
        total_shares=r.total_shares,
        record_count=r.record_count,
        kline_start=r.kline_start,
        kline_end=r.kline_end,
        latest_close=r.latest_close,
        total_mv=r.total_mv,
        pe_ttm=r.pe_ttm,
        profit_margin=(
            round(r.profit_margin, 2)
            if r.profit_margin is not None else None
        ),
        pools=pools,
        concepts=concepts,
    )


# ── 依赖注入工厂（路由层调用） ──────────────────────────────────────

def get_panel_service(
    session: AsyncSession,
) -> StockPanelAppService:
    """构造 StockPanelAppService 实例（路由 Depends 注入使用）

    若 ConceptFetcher 已注册，则注入 ConceptAppService，
    支持 with_concepts=true 的请求。
    """
    concept_app: Optional[ConceptAppService] = None
    registry = get_registry()
    if registry.has(ConceptFetcher):
        try:
            fetcher = registry.get(ConceptFetcher)
            concept_repo = ConceptRepoImpl(session)
            concept_app = ConceptAppService(repo=concept_repo, fetcher=fetcher)
        except Exception:
            concept_app = None

    return StockPanelAppService(
        session=session,
        concept_app_service=concept_app,
    )


# 类型别名，便于路由 import
PanelServiceFactory = StockPanelAppService
PanelQueryResult = StockPanelListVO
PanelQueryItem = StockPanelItemVO
PanelQueryParams = StockPanelQueryRequest