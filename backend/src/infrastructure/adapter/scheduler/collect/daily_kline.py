"""日 K 线采集任务

单元 = 1 只股票。collect_one 采单只并落库（含技术指标），业务入口
POST /klines/collect、/klines/collect/batch 与池操作经它复用。
批量 run() 保留 fetcher 池 + chunk 限频调度。

参数：
  days                  回溯天数，默认 7
  start_date/end_date   YYYYMMDD / YYYY-MM-DD / date，同时给出时优先于 days
  exchange              交易所过滤（列表），仅批量
  symbols               指定股票列表，仅批量（不给则全部上市股票）
  concurrency           并发数，上限 COLLECT_MAX_CONCURRENCY
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any, Optional

from sqlalchemy import select

from route.dto.request.kline import KlineCollectRequest
from application.service.kline_app_service import KlineAppService
from infrastructure.adapter import get_registry
from application.port.collector_port import KlineFetcher
from infrastructure.config.settings import get_settings
from infrastructure.persistence.connection import AsyncSessionLocal
from infrastructure.persistence.models.stock_info import StockInfoDB
from infrastructure.persistence.repositories.kline_repository import KlineRepoImpl
from infrastructure.persistence.repositories.stock_repository import StockRepoImpl
from infrastructure.adapter.scheduler.collect.base import (
    BaseCollectTask,
    TaskSummary,
    UnitResult,
)

logger = logging.getLogger(__name__)

UNIT_TIMEOUT = 120


def _parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date):
        return value
    s = str(value).replace("-", "")
    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def build_request(symbol: str, params: dict) -> KlineCollectRequest:
    start = _parse_date(params.get("start_date"))
    end = _parse_date(params.get("end_date"))
    if start and end:
        return KlineCollectRequest(symbol=symbol, start_date=start, end_date=end)
    return KlineCollectRequest(symbol=symbol, days=int(params.get("days", 7)))


class DailyKlineCollectTask(BaseCollectTask):
    """日 K 线采集（按 symbol 维度单元）"""

    name = "daily_kline"
    facet = "tech"
    sub_facet = "kline"
    label = "日 K 线"
    description = "5000+只股 OHLCV + 17 个技术指标（MA/EMA/MACD/RSI/KDJ/BOLL）"
    default_params = {"days": 7}

    def __init__(self) -> None:
        super().__init__()
        self._settings = get_settings()
        self._concurrency: int = 1
        self._api_interval: float = 0.3
        self._fetcher_pool: asyncio.Queue | None = None

    # ── 单元接口 ──────────────────────────────────────────────────────

    async def list_units(self, params: dict) -> list[str]:
        if params.get("symbols"):
            return [str(s).zfill(6) for s in params["symbols"]]
        async with AsyncSessionLocal() as session:
            stmt = select(StockInfoDB.symbol).where(StockInfoDB.list_status == "L")
            exchange_filter = params.get("exchange")
            if exchange_filter:
                stmt = stmt.where(StockInfoDB.exchange.in_(exchange_filter))
            result = await session.execute(stmt.order_by(StockInfoDB.symbol))
            return [r[0] for r in result.all()]

    async def collect_one(self, unit: str, params: dict) -> UnitResult:
        return await self._collect_symbol(unit, params, get_registry().get(KlineFetcher))

    async def _collect_symbol(
        self, symbol: str, params: dict, fetcher: KlineFetcher,
    ) -> UnitResult:
        async with AsyncSessionLocal() as session:
            svc = KlineAppService(KlineRepoImpl(session), StockRepoImpl(session))
            resp = await asyncio.wait_for(
                svc.collect(build_request(symbol, params), fetcher),
                timeout=UNIT_TIMEOUT,
            )
            await session.commit()
        return UnitResult(
            success=True,
            detail=resp.message,
            skipped=resp.total_count == 0,
            saved_count=resp.saved_count,
            data=resp.model_dump(),
        )

    # ── 批量：fetcher 池 + chunk 限频 ─────────────────────────────────

    async def pre_execute(self, params: dict) -> None:
        settings = self._settings
        max_conc = settings.COLLECT_MAX_CONCURRENCY
        user_conc = params.get("concurrency", settings.COLLECT_CONCURRENCY)
        self._concurrency = max(1, min(int(user_conc), max_conc))
        # interval 随并发成比例（避免触发 Tushare 限频）
        self._api_interval = max(0.1, self._concurrency * 0.15)

        self._fetcher_pool = asyncio.Queue()
        for _ in range(self._concurrency):
            self._fetcher_pool.put_nowait(get_registry().create(KlineFetcher))

        logger.info(
            "DailyKline 预热完成: 并发=%d, api_interval=%.2fs",
            self._concurrency, self._api_interval,
        )

    async def run(self, params: dict, on_unit_done) -> TaskSummary:
        assert self._fetcher_pool is not None, "pre_execute 未执行"
        pool = self._fetcher_pool
        chunk_size = self._settings.COLLECT_CHUNK_SIZE

        symbols = await self.list_units(params)
        total = len(symbols)
        exchange_filter = params.get("exchange")
        exchange_desc = ",".join(exchange_filter) if exchange_filter else "全部"
        logger.info(
            "日K采集 %d: 共 %d 只股票 (%s), 并发=%d",
            self._task_id, total, exchange_desc, self._concurrency,
        )

        sem = asyncio.Semaphore(self._concurrency)
        success = fail = skip = saved = 0

        async def one(symbol: str) -> UnitResult:
            async with sem:
                fetcher = await pool.get()
                try:
                    return await self._collect_symbol(symbol, params, fetcher)
                except asyncio.TimeoutError:
                    return UnitResult(success=False, detail=symbol, error=f"timeout {UNIT_TIMEOUT}s")
                except Exception as e:
                    return UnitResult(success=False, detail=symbol, error=str(e)[:500])
                finally:
                    await pool.put(fetcher)

        for i in range(0, total, chunk_size):
            chunk = symbols[i:i + chunk_size]
            results = await asyncio.gather(*[one(s) for s in chunk])

            for r, label in zip(results, chunk):
                await on_unit_done(r, label)
                if r.success:
                    success += 1
                    saved += r.saved_count
                    skip += 1 if r.skipped else 0
                else:
                    fail += 1

            await asyncio.sleep(self._api_interval * len(chunk))

        return TaskSummary(
            success=success,
            fail=fail,
            skip=skip,
            total_count=total,
            message=(
                f"完成 ({exchange_desc}, 并发{self._concurrency}): "
                f"成功 {success}（无数据 {skip}），失败 {fail}；写入 {saved} 条"
            ),
        )
