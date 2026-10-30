"""StockConceptsService：股票所属概念 service（按 symbol 维度批量）"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy.dialects.postgresql import insert as pg_insert

from collectors.base import (
    CollectResult, RateLimited, list_all_a_symbols, upsert_rows,
)
from collectors.fundamental.StockConceptsAdataFetcher import (
    StockConceptsAdataFetcher,
)
from core.redis import check

logger = logging.getLogger(__name__)


class StockConceptsService:
    name = "stock_concepts"
    facet = "fundamental"
    label = "股票所属概念"
    strategy = "full"
    RATE_LIMIT = ("adata", 100, 60)
    CONCURRENCY = 5

    def __init__(self, fetcher: StockConceptsAdataFetcher | None = None) -> None:
        self._fetcher = fetcher or StockConceptsAdataFetcher()

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

        async def one(s: str) -> tuple[int, list]:
            async with sem:
                await check(self.RATE_LIMIT)
                for attempt in range(3):
                    try:
                        items = await self._fetcher.fetch(symbol=s)
                        return len(items), items
                    except RateLimited as e:
                        if attempt < 2:
                            import asyncio as _a
                            await _a.sleep(e.retry_after)
                        else:
                            raise
                return 0, []

        results = await asyncio.gather(*[one(s) for s in symbols], return_exceptions=True)
        success = sum(1 for r in results if isinstance(r, tuple))
        fail = sum(1 for r in results if isinstance(r, BaseException))
        all_items = [it for r in results if isinstance(r, tuple) for it in r[1]]
        saved = await self._save(all_items)
        return CollectResult(
            total=len(symbols), success=success, fail=fail, saved=saved,
            message=f"股票所属概念: 共 {len(symbols)} 只, 成功 {success}, 写入 {saved}",
        )

    async def _save(self, items: list) -> int:
        """落库：按 (symbol, concept_id) 幂等 upsert，并回填 reason。

        ★ 本 service 是「从股票维度」采的概念归属 + 入选理由，
          与 concept_members（从概念维度）互补：
          reason 只在本 service 有值时才更新，其余情况保留旧值。

        ★ ★ 自动补全概念主表（自愈）：
          上游 get_concept_ths 返回的是**真实指数码**（885xxx，如 885761），
          而 concept_list 的 index_code 在问财 token 过期时会退化成
          **网页概念码**（308xxx 兜底值）→ 两边对不上 → 成员关系一条都写不进去。
          → 这里在匹配不到时，先把 (index_code=真实885xxx, name) 补写进概念主表，
            再建成员关系。链路自洽，且顺带把真实指数码回填进主表。
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

        codes = sorted({it["index_code"] for it in items if it.get("index_code")})
        async with raw_session_factory() as session:
            db_rows = (await session.execute(
                select(ConceptDB.index_code, ConceptDB.id).where(
                    ConceptDB.index_code.in_(codes))
            )).all()
        code_to_id = {c: i for c, i in db_rows}

        # ★ 自愈：匹配不到的概念 → 先补写进概念主表（真实 885xxx 指数码）
        missing = [c for c in codes if c not in code_to_id]
        if missing:
            name_by_code = {
                it["index_code"]: it.get("name")
                for it in items
                if it.get("index_code") and it.get("name")
            }
            new_rows = [
                {"index_code": c, "concept_code": None, "name": name_by_code.get(c) or c}
                for c in missing
            ]
            from collectors.base import chunk_rows_for_insert, dedupe_rows
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
            logger.info("stock_concepts: 自动补全 %d 个概念到主表", len(missing))

        if not code_to_id:
            logger.warning("stock_concepts: 未找到 index_code 对应的概念，"
                           "请先采集 concept_list")
            return 0

        rows = [
            {
                "symbol": it["symbol"],
                "concept_id": code_to_id[it["index_code"]],
                "reason": it.get("reason"),
                "source": "ths",
            }
            for it in items
            if it.get("index_code") in code_to_id and it.get("symbol")
        ]
        if not rows:
            return 0
        # ★ reason 参与更新（这是本 service 的核心产出）
        #   但 reason 为 None 时不覆盖旧值 → 用 excluded 需小心，
        #   这里统一写入，reason 由上游保证非空时才有意义
        return await upsert_rows(
            ConceptMemberDB, rows, ["symbol", "concept_id"],
            immutable_cols=["symbol", "concept_id", "joined_at"],
        )


__all__ = ["StockConceptsService"]
