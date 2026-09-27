"""StockPanel 应用服务

职责单一：把"分页 + 多表快照 + 批量池"组合查询的结果组装为分页 VO。
不做单表 CRUD，不做领域事件。

对应路由：GET /api/v1/stock-panel/

08concept 增量：
- 通过注入 ConceptBriefService（domain）做"主概念"摘要排序，构造 ConceptMainVO + overflow

DDD 改造：
- 不再依赖 application.service.concept_app_service（跨应用服务依赖）
- 改注入 domain.concept.service.ConceptBriefService（领域服务）
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.panel import (
    StockPanelItemVO,
    StockPanelListVO,
    StockPanelQueryRequest,
)
from application.dto.pool import PoolMembershipVO
from domain.concept.service import ConceptBriefService
from domain.concept.value_objects import ConceptBriefVO, ConceptMainVO
from domain.panel.repository import StockPanelComposeRepository
from domain.panel.value_objects import StockPanelRow
from infrastructure.persistence.repositories.concept_repository import ConceptRepoImpl
from infrastructure.persistence.repositories.panel_compose_repository import (
    StockPanelComposeRepoImpl,
)


# 列表行内"主概念"列展示上限（可被外部覆盖）
DEFAULT_MAIN_CONCEPT_TOP_K = 3


class StockPanelAppService:
    """列表面板应用服务

    依赖（构造注入）：
    - session:         AsyncSession（数据库会话）
    - concept_repo:    ConceptRepository（领域接口）
    - brief_service:   ConceptBriefService（领域服务，做主概念排序）
    - top_k:           主概念展示上限
    """

    def __init__(
        self,
        session: AsyncSession,
        concept_repo: Optional[ConceptRepoImpl] = None,
        brief_service: Optional[ConceptBriefService] = None,
        top_k: int = DEFAULT_MAIN_CONCEPT_TOP_K,
    ):
        self._session = session
        self._concept_repo = concept_repo or ConceptRepoImpl(session)
        self._brief_service = brief_service or ConceptBriefService(top_k=top_k)
        self._top_k = top_k

        self._repo: StockPanelComposeRepository = StockPanelComposeRepoImpl(
            session,
            concept_repo=self._concept_repo,
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
        if req.with_concepts and rows and self._concept_repo is not None:
            concept_map = await self._repo.list_concepts_by_symbols(symbols)

        # 09concept：批量取概念快照（最多 1 次额外 SQL，避免每行 N+1）
        snapshot_map: dict[str, dict] = {}
        if concept_map and self._concept_repo is not None:
            all_names: set[str] = set()
            for briefs in concept_map.values():
                for b in briefs:
                    all_names.add(b.name)
            if all_names:
                snapshot_map = await self._repo.list_snapshots_for_names(list(all_names))

        # 08concept：用 ConceptBriefService（domain）做主概念排序
        main_concept_map = self._brief_service.build_main_concepts(
            concept_map,
            snapshot_map=snapshot_map,
            top_k=self._top_k,
        )

        items = [
            _to_vo(
                r,
                pool_map.get(r.symbol, []),
                main_concept_map.get(r.symbol, ([], 0)),
            )
            for r in rows
        ]
        return StockPanelListVO.from_list(items, total, req.page, req.page_size)


def _to_vo(
    r: StockPanelRow,
    pools: list[PoolMembershipVO],
    main_concepts_with_overflow: tuple[list[ConceptMainVO], int],
) -> StockPanelItemVO:
    """StockPanelRow → StockPanelItemVO（字段 1:1 + pools/concepts 注入）"""
    main_concepts, overflow = main_concepts_with_overflow
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
        concepts=main_concepts,
        concepts_overflow=overflow,
    )
