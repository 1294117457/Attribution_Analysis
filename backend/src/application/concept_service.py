"""概念应用服务

配套设计文档：
  docs/dev/06gainian/03-application-and-route-design.md §2.1
"""

from __future__ import annotations

import logging
from typing import Optional

from application.dto.concept import (
    ConceptDetailVO,
    ConceptItemVO,
    ConceptMemberVO,
    ConceptQueryRequest,
    ConceptSyncRequest,
    ConceptSyncResultVO,
    ConceptTabContentVO,
    ConceptTabSectionVO,
    CONCEPT_TYPE_LABELS,
    CONCEPT_TYPE_ORDER,
)
from application.dto.page import Page
from domain.concept.exceptions import ConceptNotFoundError
from domain.concept.repository import ConceptRepository
from domain.concept.value_objects import ConceptBriefVO
from infrastructure.collectors.protocols import ConceptFetcher
from infrastructure.repositories.concept_repository import ConceptRepoImpl
from infrastructure.tasks.concept_sync_operation import ConceptSyncOperation

logger = logging.getLogger(__name__)


class ConceptAppService:
    """概念应用服务

    职责：
    - 同步：触发 AKShare 采集器同步概念数据
    - 查询：列表 / 详情 / 反查（供 panel 调用）
    """

    def __init__(
        self,
        repo: ConceptRepository,
        fetcher: ConceptFetcher,
    ):
        self._repo = repo
        self._fetcher = fetcher

    # ── 同步 ─────────────────────────────────────────

    async def sync_concepts(self, req: ConceptSyncRequest) -> ConceptSyncResultVO:
        """全量/增量同步概念数据"""
        operation = ConceptSyncOperation(repo=self._repo, fetcher=self._fetcher)
        result = await operation.sync_all()

        return ConceptSyncResultVO(
            total_concepts=result.total_concepts,
            total_members=result.total_members,
            failed_concepts=result.failed_concepts,
            elapsed_ms=result.elapsed_ms,
            synced_at=result.synced_at,
        )

    # ── 查询 ─────────────────────────────────────────

    async def query_concepts(
        self, req: ConceptQueryRequest
    ) -> Page[ConceptItemVO]:
        """分页查询概念列表"""
        concepts, total = await self._repo.list_concepts(
            q=req.q,
            source=req.source,
            is_active=req.is_active,
            page=req.page,
            page_size=req.page_size,
        )

        items = [
            ConceptItemVO(
                concept_id=c.id,
                name=c.name,
                source=c.source.value,
                concept_type=c.concept_type.value if hasattr(c.concept_type, "value") else c.concept_type,
                stock_count=c.stock_count,
                description=c.description,
                is_active=c.is_active,
                last_synced_at=c.last_synced_at,
                first_seen_at=c.first_seen_at,
            )
            for c in concepts
        ]

        return Page[ConceptItemVO].from_list(
            items,
            total,
            req.page,
            req.page_size,
        )

    async def get_concept_detail(
        self, name: str, source: str = "em"
    ) -> ConceptDetailVO:
        """概念详情（含成分股）"""
        concept = await self._repo.get_concept_by_name(name=name, source=source)
        if not concept:
            raise ConceptNotFoundError(name=name)

        # 获取成分股（实时拉取）
        stock_bos = self._fetcher.fetch_concept_stocks(name)
        members = [
            ConceptMemberVO(
                symbol=s.symbol,
                name=s.name,
                rank=s.rank,
                latest_price=s.latest_price,
            )
            for s in stock_bos
        ]

        return ConceptDetailVO(
            concept_id=concept.id,
            name=concept.name,
            source=concept.source.value,
            concept_type=concept.concept_type.value if hasattr(concept.concept_type, "value") else concept.concept_type,
            stock_count=concept.stock_count,
            description=concept.description,
            is_active=concept.is_active,
            last_synced_at=concept.last_synced_at,
            first_seen_at=concept.first_seen_at,
            members=members,
        )

    # ── 反向查询（供 panel 复用）──────────────────────

    async def list_for_symbol(self, symbol: str) -> list[ConceptBriefVO]:
        """单只股票所属的所有活跃概念"""
        return await self._repo.list_concepts_by_symbol(symbol)

    async def list_for_symbols(
        self, symbols: list[str]
    ) -> dict[str, list[ConceptBriefVO]]:
        """批量反向查询（避免 N+1）"""
        return await self._repo.list_concepts_by_symbols(symbols)

    # ── 详情抽屉「概念」Tab 专用 ──────────────────────

    async def get_tab_content_for_symbol(
        self,
        symbol: str,
        stock_name: Optional[str] = None,
    ) -> ConceptTabContentVO:
        """详情抽屉「概念」Tab 的完整渲染模型

        步骤：
        ① 拉取该股票所属的所有活跃概念（含 concept_type / description）
        ② 按 concept_type 分组，按预定顺序排序（industry → theme → style → region → event → other）
        ③ 组装为 ConceptTabContentVO，前端 ConceptTab.vue 直接消费
        """
        grouped_vos = await self._repo.list_concepts_by_symbol_grouped(symbol)

        bucket: dict[str, list] = {t: [] for t in CONCEPT_TYPE_ORDER}
        for vo in grouped_vos:
            bucket.setdefault(vo.concept_type, []).append(vo)

        sections = [
            ConceptTabSectionVO(
                type=t,
                type_label=CONCEPT_TYPE_LABELS.get(t, t),
                concepts=[
                    {
                        "concept_id": c.concept_id,
                        "name": c.name,
                        "source": c.source,
                        "concept_type": c.concept_type,
                        "description": c.description,
                    }
                    for c in sorted(bucket[t], key=lambda x: x.name)
                ],
            )
            for t in CONCEPT_TYPE_ORDER
            if bucket[t]
        ]

        return ConceptTabContentVO(
            symbol=symbol,
            stock_name=stock_name or "",
            sections=sections,
            total_count=sum(len(s.concepts) for s in sections),
        )


# ── 依赖注入工厂 ──────────────────────────────────────

async def get_concept_app_service(
    session,  # AsyncSession
) -> ConceptAppService:
    """构造 ConceptAppService 实例

    从 FetcherRegistry 获取已注册的 fetcher。
    """
    from infrastructure.collectors.registry import get_registry
    from infrastructure.collectors.protocols import ConceptFetcher

    repo = ConceptRepoImpl(session)
    registry = get_registry()
    fetcher = registry.get(ConceptFetcher)
    return ConceptAppService(repo=repo, fetcher=fetcher)
