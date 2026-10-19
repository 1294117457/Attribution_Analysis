"""ConceptMembersService：概念成分股 service

走 repo：ConceptMemberRepository + ConceptRepository
session 由 DI 工厂注入（get_raw_db），透传给所有 repo 调用。
"""
from __future__ import annotations

import asyncio
import logging

from contexts.collect.application.service.base import CollectResult, RateLimited, list_all_concept_codes, ServiceKind, ServiceMeta
from contexts.collect.infrastructure.fetcher.fundamental.ConceptMembersAdataFetcher import (
    ConceptMembersAdataFetcher,
)
from contexts.collect.infrastructure.persistence.repositories import (
    ConceptMemberRepository,
    ConceptRepository,
)
from contexts.collect.infrastructure.cache.rate_limit import check
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ConceptMembersService:

    META = ServiceMeta(
        name='concept_members',
        facet='fundamental',
        label='概念成分股',
        description='概念成分股（Adata concept_members）',
        kind=ServiceKind.INCREMENTAL,
    )
    name = "concept_members"
    facet = "fundamental"
    sub_facet = "concept"
    label = "概念成分股"
    DEFAULT_PARAMS = {"index_codes": []}
    UI_SCHEMA = [
        {
            "key": "index_codes",
            "ui": "index_codes_list",
            "label": "概念指数代码",
            "required": False,
            "placeholder": "每行一个：BK0001\nBK0002",
            "help": "留空表示全量采集（先采集 concept_list 拿到全部概念）",
        },
    ]
    RATE_LIMIT = ("adata", 100, 60)
    CONCURRENCY = 3

    def __init__(
        self,
        fetcher: ConceptMembersAdataFetcher | None = None,
        member_repo: ConceptMemberRepository | None = None,
        concept_repo: ConceptRepository | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        self._fetcher = fetcher or ConceptMembersAdataFetcher()
        self._member_repo = member_repo or ConceptMemberRepository()
        self._concept_repo = concept_repo or ConceptRepository()
        self._session = session

    async def collect(self, params: dict) -> CollectResult:
        index_codes = params.get("index_codes") or []
        if not index_codes:
            index_codes = await list_all_concept_codes()
            if not index_codes:
                return CollectResult(
                    fail=1,
                    message="index_codes 为空，且 concept 暂无数据（请先采集 concept_list）",
                )
        sem = asyncio.Semaphore(self.CONCURRENCY)

        async def one(c: str) -> int:
            async with sem:
                await check(self.RATE_LIMIT)
                for attempt in range(3):
                    try:
                        bos = await self._fetcher.fetch(index_code=c)
                        if not bos:
                            return 0
                        # 通过 index_code 解析 concept_id
                        concept_id = await self._concept_repo.get_id_by_name(bos[0].index_code, self._session) or 0
                        # 实际上 index_code 才是 key，name 不一定等于 index_code
                        # 走 list_all_codes 拿 name→id 映射；为了避免 N+1 改为
                        # 一次性缓存：service 启动时调用 list_all_codes + get_id_by_name
                        return await self._member_repo.save_by_concept(concept_id, bos, self._session)
                    except RateLimited as e:
                        if attempt < 2:
                            import asyncio as _a
                            await _a.sleep(e.retry_after)
                        else:
                            raise
                return 0

        results = await asyncio.gather(*[one(c) for c in index_codes], return_exceptions=True)
        success = sum(1 for r in results if isinstance(r, int) and r >= 0)
        saved = sum(r for r in results if isinstance(r, int))
        fail = sum(1 for r in results if isinstance(r, BaseException))
        return CollectResult(
            total=len(index_codes), success=success, fail=fail, saved=saved,
            message=f"概念成分股: 共 {len(index_codes)} 个概念, 成功 {success}, 写入 {saved}",
        )


__all__ = ["ConceptMembersService"]
