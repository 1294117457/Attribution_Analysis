"""ConceptMembersService：概念成分股 service（按 index_code 维度批量）"""
from __future__ import annotations

import asyncio
import logging

from collectors.base import (
    CollectResult, RateLimited, list_all_concept_codes, upsert_rows,
)
from collectors.fundamental.ConceptMembersAdataFetcher import (
    ConceptMembersAdataFetcher,
)
from core.redis import check

logger = logging.getLogger(__name__)


class ConceptMembersService:
    name = "concept_members"
    facet = "fundamental"
    label = "概念成分股"
    strategy = "full"
    RATE_LIMIT = ("adata", 100, 60)
    CONCURRENCY = 3

    def __init__(self, fetcher: ConceptMembersAdataFetcher | None = None) -> None:
        self._fetcher = fetcher or ConceptMembersAdataFetcher()

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

        async def one(c: str) -> tuple[int, list]:
            async with sem:
                await check(self.RATE_LIMIT)
                for attempt in range(3):
                    try:
                        items = await self._fetcher.fetch(index_code=c)
                        return len(items), items
                    except RateLimited as e:
                        if attempt < 2:
                            import asyncio as _a
                            await _a.sleep(e.retry_after)
                        else:
                            raise
                return 0, []

        results = await asyncio.gather(*[one(c) for c in index_codes], return_exceptions=True)
        success = sum(1 for r in results if isinstance(r, tuple))
        fail = sum(1 for r in results if isinstance(r, BaseException))
        all_items = [it for r in results if isinstance(r, tuple) for it in r[1]]
        saved = await self._save(all_items)
        return CollectResult(
            total=len(index_codes), success=success, fail=fail, saved=saved,
            message=f"概念成分股: 共 {len(index_codes)} 个概念, 成功 {success}, 写入 {saved}",
        )

    async def _save(self, items: list) -> int:
        """落库：按 (symbol, concept_id) 幂等 upsert。

        ★ concept_id 通过 index_code 关联 fundamental_concept.id。
        ★ 保留 reason：upsert 时不覆盖已有 reason（成分股接口不提供 reason）。
        """
        if not items:
            return 0
        try:
            from models.concept_compat import (
                ConceptDB,
                ConceptMemberDB,
            )
        except ImportError:
            logger.debug("fundamental_concept_member 表未建，跳过入库")
            return 0

        from sqlalchemy import select

        from core.db import raw_session_factory

        # ① 解析 index_code → concept_id
        codes = sorted({it["index_code"] for it in items if it.get("index_code")})
        async with raw_session_factory() as session:
            db_rows = (await session.execute(
                select(ConceptDB.index_code, ConceptDB.id).where(
                    ConceptDB.index_code.in_(codes))
            )).all()
        code_to_id = {c: i for c, i in db_rows}

        # ★ 自愈：匹配不到的概念 → 先补写进概念主表。
        #   concept_list 的 index_code 在问财 token 过期时会退化成 308xxx 兜底值，
        #   而本 service 用的是真实 885xxx 指数码 → 两边对不上 → 成员关系写不进去。
        #   → 补写主表（真实 885xxx），让链路自洽。
        missing = [c for c in codes if c not in code_to_id]
        if missing:
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            from collectors.base import chunk_rows_for_insert, dedupe_rows
            new_rows = [{"index_code": c, "concept_code": None, "name": c}
                        for c in missing]
            async with raw_session_factory() as session:
                for chunk in chunk_rows_for_insert(
                    ConceptDB, dedupe_rows(new_rows, ["index_code"])
                ):
                    stmt = pg_insert(ConceptDB).values(chunk)
                    update_cols = {c.name: stmt.excluded[c.name]
                                   for c in ConceptDB.__table__.columns
                                   if c.name not in ("id", "index_code", "created_at")}
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["index_code"], set_=update_cols)
                    await session.execute(stmt)
                await session.commit()
            async with raw_session_factory() as session:
                db_rows = (await session.execute(
                    select(ConceptDB.index_code, ConceptDB.id).where(
                        ConceptDB.index_code.in_(codes))
                )).all()
            code_to_id = {c: i for c, i in db_rows}
            logger.info("concept_members: 自动补全 %d 个概念到主表", len(missing))

        if not code_to_id:
            logger.warning("concept_members: 未找到任何 index_code 对应的概念，"
                           "请先采集 concept_list")
            return 0

        rows = [
            {
                "symbol": it["symbol"],
                "concept_id": code_to_id[it["index_code"]],
                "source": "ths",
            }
            for it in items
            if it.get("index_code") in code_to_id and it.get("symbol")
        ]
        if not rows:
            return 0
        # ★ reason 不在更新列里 → 已有 reason 保留（成分股接口不提供 reason）
        return await upsert_rows(
            ConceptMemberDB, rows, ["symbol", "concept_id"],
            immutable_cols=["symbol", "concept_id", "reason", "joined_at"],
        )


__all__ = ["ConceptMembersService"]
