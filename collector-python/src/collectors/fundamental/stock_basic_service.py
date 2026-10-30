"""StockBasicService：股票基本信息 service（写库 + 实时查询）"""
from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Optional

from collectors.base import CollectResult, mark_outside
from collectors.fundamental.StockBasicTushareFetcher import (
    StockBasicTushareFetcher,
)
from collectors.stock_info_repo import (
    StockInfoRepository,
)
from core.redis import check

logger = logging.getLogger(__name__)


def _stock_basic_to_dict(bo) -> dict:
    # ★ list_date / delist_date 必须传 **date 对象**，不能传 ISO 字符串。
    #   表列类型是 Date → asyncpg 收到 str 会报：
    #     "invalid input for query argument $8: '2026-09-17'
    #      ('str' object has no attribute 'toordinal')"
    #   （此前 isoformat() 化的写法让 stock_basic 全量采集 100% 失败。）
    return {
        "symbol": bo.symbol,
        "ts_code": bo.ts_code,
        "name": bo.name,
        "area": bo.area,
        "industry": bo.industry,
        "market": bo.market,
        "exchange": bo.exchange,
        "list_date": bo.list_date,
        "delist_date": bo.delist_date,
        "list_status": bo.list_status,
        "is_hs": bo.is_hs,
        "act_name": bo.act_name,
        "act_ent_type": bo.act_ent_type,
    }


class StockBasicService:
    name = "stock_basic"
    facet = "fundamental"
    label = "股票基本信息"
    description = "全 A 股基本信息（Tushare stock_basic）"
    strategy = "full"
    QUERYABLE = True
    CLEAR_MODE = "domain"

    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 1

    def __init__(
        self,
        fetcher: StockBasicTushareFetcher | None = None,
        stock_repo: StockInfoRepository | None = None,
    ) -> None:
        self._fetcher = fetcher or StockBasicTushareFetcher()
        self._stock_repo = stock_repo or StockInfoRepository()
        # ★ 缓存本次覆盖到的 symbol 集合 + 原始 BO：
        #   clear() 与 collect() 复用同一实例，避免各拉一次上游（省一半 tushare 配额）。
        self._covered_symbols: list[str] = []
        self._cached_bos: list | None = None

    async def collect(self, params: dict) -> CollectResult:
        # ★ list_status 默认 'L'（在上市）——原先由 DEFAULT_PARAMS 提供，
        #   DEFAULT_PARAMS 已删除，兜底直接写在这里。
        list_status = str(params.get("list_status") or "L")
        fetch_params = {"list_status": list_status}
        await check(self.RATE_LIMIT)
        # ★ 复用 clear() 已拉到的上游结果（同一实例）
        bos = self._cached_bos
        if bos is None:
            bos = await self._fetch_with_retry(fetch_params, retries=2)
            self._cached_bos = bos
        if not bos:
            return CollectResult(skip=1, message="empty")
        rows = [_stock_basic_to_dict(bo) for bo in bos]
        # ★ 记录本次覆盖域，供 clear() 使用（同一实例内）
        self._covered_symbols = [r["symbol"] for r in rows]
        saved = await self._stock_repo.save_batch(rows)
        return CollectResult(
            total=1, success=1, saved=saved,
            message=f"股票基本信息: 同步 {len(bos)} 条, 写入 {saved} 条",
        )

    async def get(self, symbol: str) -> Optional[dict]:
        return await self._stock_repo.find(str(symbol).zfill(6))

    async def clear(self, params: dict) -> int:
        """全量覆盖前的清理：把「本次覆盖域外」的残留行标记为退市。

        ★ 语义选择：**不物理删除**退市股票，只把 list_status 置为 'D'。
          理由：历史行情/财报等表仍按 symbol 关联这些股票，
          物理删除会产生孤儿行，把整条分析链路打断。
        ★ 窄化：只处理 list_status='L'（在市）的行——已退市的不重复处理。
        ★ 空覆盖集直接返回 0（绝不因为上游空返回就清空全表）。
        """
        list_status = (params or {}).get("list_status", "L")
        if list_status != "L":
            # 只支持在市口径的覆盖；其它口径不做清理
            return 0

        # ★ 复用同一实例缓存的上游结果（避免两次拉 tushare）
        if self._cached_bos is None:
            await check(self.RATE_LIMIT)
            self._cached_bos = await self._fetch_with_retry(
                {"list_status": list_status}, retries=2)
        symbols = list(self._covered_symbols) or [
            str(bo.symbol).zfill(6) for bo in self._cached_bos
        ]
        if not symbols:
            # 上游返回空 → 绝不清理（避免清空全表）
            logger.warning("stock_basic.clear: 上游返回空，跳过清理")
            return 0

        # ★ 复用共享 helper：把覆盖域外的在市股票标记为退市
        #   （不物理删除 —— 历史行情/财报仍按 symbol 关联这些股票）
        from models.stock_info import StockInfoDB

        return await mark_outside(
            StockInfoDB,
            "symbol",
            symbols,
            {"list_status": "D", "delist_date": date.today()},
            where_extra=(StockInfoDB.list_status == "L"),
        )
    async def _fetch_with_retry(self, params: dict, retries: int) -> list:
        last_err: Optional[Exception] = None
        for attempt in range(retries + 1):
            try:
                return await self._fetcher.fetch(**params)
            except Exception as e:
                last_err = e
                if attempt < retries:
                    await asyncio.sleep(2.0 * (attempt + 1))
                    continue
                raise
        if last_err:
            raise last_err
        return []


__all__ = ["StockBasicService"]
