"""StockConceptsService：股票所属概念 service

走 repo：StockConceptRepository + ConceptRepository
session 由 DI 工厂注入（get_raw_db），透传给所有 repo 调用。
"""
from __future__ import annotations

import asyncio
import logging

from contexts.collect.application.service.base import CollectResult, RateLimited, list_all_a_symbols, ServiceKind, ServiceMeta
from contexts.collect.infrastructure.fetcher.fundamental.StockConceptsAdataFetcher import (
    StockConceptsAdataFetcher,
)
from contexts.collect.infrastructure.persistence.repositories import (
    ConceptRepository,
    StockConceptRepository,
)
from contexts.collect.infrastructure.cache.rate_limit import check
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class StockConceptsService:

    META = ServiceMeta(
        name='stock_concepts',
        facet='fundamental',
        label='股票所属概念',
        description='股票所属概念（Adata stock_concepts）',
        kind=ServiceKind.INCREMENTAL,
    )
    name = "stock_concepts"
    facet = "fundamental"
    sub_facet = "concept"
    label = "股票所属概念"
    DEFAULT_PARAMS = {"symbols": []}
    UI_SCHEMA = [
        {
            "key": "symbols",
            "ui": "symbols_list",
            "label": "股票代码",
            "required": True,
            "placeholder": "每行一只：000001\n000002\n600000",
            "help": "必填，至少一只股票",
        },
    ]
    RATE_LIMIT = ("adata", 100, 60)
    CONCURRENCY = 5

    def __init__(
        self,
        fetcher: StockConceptsAdataFetcher | None = None,
        stock_concept_repo: StockConceptRepository | None = None,
        concept_repo: ConceptRepository | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        self._fetcher = fetcher or StockConceptsAdataFetcher()
        self._stock_concept_repo = stock_concept_repo or StockConceptRepository()
        self._concept_repo = concept_repo or ConceptRepository()
        self._session = session

    async def collect(self, params: dict) -> CollectResult:
        symbols = params.get("symbols") or []
        if not symbols:
            symbols = await list_all_a_symbols()
            if not symbols:
                return CollectResult(
                    fail=1,
                    message="symbols 为空，且 stock_basic 暂无数据（请先采集 stock_basic）",
                )
        symbols = [str(s).zfill(6) for s in symbols]
        sem = asyncio.Semaphore(self.CONCURRENCY)

        # 一次性预拉 concept_id_map（按 name → id）
        concept_id_map: dict[str, int] = {}
        all_codes = await self._concept_repo.list_all_codes(self._session)
        # 实际拿 name → id 需要 ConceptRepository.get_id_by_name(name) 多次，
        # 简化：让 service 端缓存；本批只做单 symbol 增量处理

        async def one(s: str) -> int:
            async with sem:
                await check(self.RATE_LIMIT)
                for attempt in range(3):
                    try:
                        items = await self._fetcher.fetch(symbol=s)
                        if not items:
                            return 0
                        # 逐条解析 name → concept_id
                        for it in items:
                            name = it.get("name")
                            if name and name not in concept_id_map:
                                cid = await self._concept_repo.get_id_by_name(name, self._session)
                                if cid is not None:
                                    concept_id_map[name] = cid
                        return await self._stock_concept_repo.upsert_by_concept_map(
                            items, concept_id_map, self._session,
                        )
                    except RateLimited as e:
                        if attempt < 2:
                            import asyncio as _a
                            await _a.sleep(e.retry_after)
                        else:
                            raise
                return 0

        results = await asyncio.gather(*[one(s) for s in symbols], return_exceptions=True)
        success = sum(1 for r in results if isinstance(r, int) and r >= 0)
        saved = sum(r for r in results if isinstance(r, int))
        fail = sum(1 for r in results if isinstance(r, BaseException))
        return CollectResult(
            total=len(symbols), success=success, fail=fail, saved=saved,
            message=f"股票所属概念: 共 {len(symbols)} 只, 成功 {success}, 写入 {saved}",
        )


__all__ = ["StockConceptsService"]
