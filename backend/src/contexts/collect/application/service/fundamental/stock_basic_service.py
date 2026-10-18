"""StockBasicService：股票基本信息 service（写库 + 实时查询）"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from contexts.collect.application.service.base import CollectResult
from contexts.collect.infrastructure.fetcher.fundamental.StockBasicTushareFetcher import (
    StockBasicTushareFetcher,
)
from contexts.collect.infrastructure.persistence.repositories.stock_info_repo import (
    StockInfoRepository,
)
from contexts.collect.infrastructure.cache.rate_limit import check

logger = logging.getLogger(__name__)


def _stock_basic_to_dict(bo) -> dict:
    return {
        "symbol": bo.symbol,
        "ts_code": bo.ts_code,
        "name": bo.name,
        "area": bo.area,
        "industry": bo.industry,
        "market": bo.market,
        "exchange": bo.exchange,
        "list_date": bo.list_date.isoformat() if bo.list_date else None,
        "delist_date": bo.delist_date.isoformat() if bo.delist_date else None,
        "list_status": bo.list_status,
        "is_hs": bo.is_hs,
        "act_name": bo.act_name,
        "act_ent_type": bo.act_ent_type,
    }


class StockBasicService:
    name = "stock_basic"
    facet = "fundamental"
    sub_facet = "stock"
    label = "股票基本信息"
    description = "全 A 股基本信息（Tushare stock_basic）"

    DEFAULT_PARAMS = {"list_status": "L"}
    RATE_LIMIT = ("tushare", 200, 60)
    CONCURRENCY = 1

    def __init__(
        self,
        fetcher: StockBasicTushareFetcher | None = None,
        stock_repo: StockInfoRepository | None = None,
    ) -> None:
        self._fetcher = fetcher or StockBasicTushareFetcher()
        self._stock_repo = stock_repo or StockInfoRepository()

    async def collect(self, params: dict) -> CollectResult:
        merged = {**self.DEFAULT_PARAMS, **params}
        fetch_params = {
            k: v for k, v in merged.items()
            if k in ("list_status",)
        }
        await check(self.RATE_LIMIT)
        bos = await self._fetch_with_retry(fetch_params, retries=2)
        if not bos:
            return CollectResult(skip=1, message="empty")
        rows = [_stock_basic_to_dict(bo) for bo in bos]
        saved = await self._stock_repo.save_batch(rows)
        return CollectResult(
            total=1, success=1, saved=saved,
            message=f"股票基本信息: 同步 {len(bos)} 条, 写入 {saved} 条",
        )

    async def get(self, symbol: str) -> Optional[dict]:
        return await self._stock_repo.find(str(symbol).zfill(6))

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
