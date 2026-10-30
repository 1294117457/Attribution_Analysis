"""ConceptListService：概念清单 service（adata 一次性全量）"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.db import raw_session_factory
from collectors.base import CollectResult, RateLimited, delete_outside
from collectors.fundamental.ConceptListAdataFetcher import (
    ConceptListAdataFetcher,
)
from core.redis import check

logger = logging.getLogger(__name__)

# ★ 清理所需的最小覆盖集条数（本表正常规模 300+）
#   低于此值 → 判定为上游残缺响应 → 跳过 delete_outside，避免误删
MIN_CLEAN_COVERAGE = 50

# ★ 上游空响应重试（每轮都过 Redis 限流）
_EMPTY_RETRY_ATTEMPTS = 3
_EMPTY_RETRY_SLEEP_SECONDS = 5


class ConceptListService:
    name = "concept_list"
    facet = "fundamental"
    label = "概念清单"
    strategy = "full"
    CLEAR_MODE = "domain"
    RATE_LIMIT = ("adata", 100, 60)
    CONCURRENCY = 1

    def __init__(self, fetcher: ConceptListAdataFetcher | None = None) -> None:
        self._fetcher = fetcher or ConceptListAdataFetcher()
        # ★ 缓存本次覆盖到的 index_code 集合 + 原始条目
        #   （clear/collect 复用同一实例，避免两次拉上游）
        self._covered_codes: list[str] = []
        self._cached_items: list | None = None

    async def _fetch_with_retry(self) -> list:
        """拉上游概念清单，空结果时重试（每轮都过 Redis 限流）。

        ★ 为什么重试必须在 service 层：fetcher 内重试会绕过限流，
          把 1 次服务调用放大成 N 次上游请求 → 触发同花顺按 IP 限流
          → 反而一直拿不到数据。
        """
        if self._cached_items is not None:
            return self._cached_items
        items: list = []
        for attempt in range(_EMPTY_RETRY_ATTEMPTS):
            await check(self.RATE_LIMIT)
            items = await self._fetcher.fetch()
            if items:
                break
            logger.warning(
                "concept_list: 上游返回空（第 %d/%d 次），等待后重试",
                attempt + 1, _EMPTY_RETRY_ATTEMPTS,
            )
            await asyncio.sleep(_EMPTY_RETRY_SLEEP_SECONDS * (attempt + 1))
        self._cached_items = items
        return items

    async def collect(self, params: dict) -> CollectResult:
        items = await self._fetch_with_retry()

        if not items:
            return CollectResult(
                total=1, skip=1,
                message="概念清单: 上游连续返回空（同花顺页面接口被限流），"
                        "本次未采集到数据",
            )

        self._covered_codes = [it["index_code"] for it in items if it.get("index_code")]
        saved = await self._save(items)
        return CollectResult(
            total=1, success=1, saved=saved,
            message=f"概念清单: {len(items)} 条, 写入 {saved}",
        )

    async def clear(self, params: dict) -> int:
        """全量覆盖前的清理：删除「本次覆盖域外」的废弃概念。

        ★ 窄化：只删 fundamental_concept 里 index_code 不在本次集合中的行。
        ★ 空覆盖集直接返回 0（绝不因为上游空返回就清空全表）。
        ★ 概念成分股（fundamental_concept_member）会因外键/引用残留，
          这里只清主表，成分股残留由 concept_members 的全量采集自然收敛。
        """
        if self._cached_items is None:
            await self._fetch_with_retry()
        codes = list(self._covered_codes) or [
            it["index_code"] for it in self._cached_items if it.get("index_code")
        ]
        if not codes:
            logger.warning("concept_list.clear: 上游返回空，跳过清理")
            return 0

        # ★ 复用共享 helper：只清主表（成分股由 concept_members 全量采集自然收敛）
        from models.concept_compat import ConceptDB

        # ★ ★ 残缺覆盖保护：
        #   上游「同花顺概念列表」是**间歇性返回残缺**的（问财接口 token 过期时
        #   index_code 整列变 NaN，页面接口被限流时直接返回空）。
        #   本表的正常规模是 300+ 条；若本次只拿到个位数，说明是残缺响应
        #   —— 此时执行 delete_outside 会把库里其它概念**批量删光**（数据丢失）。
        #   → 覆盖集明显偏小时跳过清理，只做 upsert（新增/更新）。
        if len(codes) < MIN_CLEAN_COVERAGE:
            logger.warning(
                "concept_list.clear: 本次覆盖集只有 %d 条（阈值 %d），"
                "判定为上游残缺响应，跳过清理以免误删",
                len(codes), MIN_CLEAN_COVERAGE,
            )
            return 0

        return await delete_outside(ConceptDB, "index_code", codes)

    async def _save(self, items) -> int:
        if not items:
            return 0
        from models.concept_compat import ConceptDB
        rows = [
            {"index_code": it["index_code"], "concept_code": it.get("concept_code"),
             "name": it["name"]}
            for it in items
        ]
        async with raw_session_factory() as session:
            # ★ 分块（防 PG 参数上限）+ 按 index_code 去重（防 ON CONFLICT 二次命中）
            from collectors.base import chunk_rows_for_insert, dedupe_rows

            total = 0
            for chunk in chunk_rows_for_insert(
                ConceptDB, dedupe_rows(rows, ["index_code"])
            ):
                stmt = pg_insert(ConceptDB).values(chunk)
                update_cols = {c.name: stmt.excluded[c.name] for c in ConceptDB.__table__.columns
                               if c.name not in ("id", "index_code", "created_at")}
                stmt = stmt.on_conflict_do_update(
                    index_elements=["index_code"],
                    set_=update_cols,
                )
                r = await session.execute(stmt)
                total += r.rowcount or 0
            await session.commit()
            return total


__all__ = ["ConceptListService"]
