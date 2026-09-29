"""季报财务采集任务（Tushare income · 利润表）

单元 = 1 只股票（按单只调用 income；按报告期拉全市场的 income_vip 需 5000 积分，当前账号无权限）。
只采合并报表 report_type=1，写 fin_reports 的利润表列；面板净利润率 = n_income / revenue × 100。

参数：
  years         按公告日回溯年数，默认 1（覆盖最近 4 个报告期）；回填用 3
  symbol        只采单只股票
  only_missing  跳过库中已有财报的股票（回填断点续采）
  limit         只采前 N 只（调试）

配套设计文档：docs/dev/step2/03进一步优化/01净利润采集修复.md
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select

from application.port.collector_port import FinReportFetcher, RateLimitError
from infrastructure.adapter import get_registry
from infrastructure.adapter.scheduler.collect.base import (
    BaseCollectTask,
    Cancelled,
    TaskSummary,
    UnitResult,
    is_cancelled,
)
from infrastructure.adapter.tushare.fetcher import symbol_to_ts_code
from infrastructure.persistence.connection import AsyncSessionLocal
from infrastructure.persistence.models.stock_info import StockInfoDB
from infrastructure.persistence.repositories.fin_report_repository import FinReportRepoImpl

logger = logging.getLogger(__name__)

# 触发 Tushare 每分钟限频后的等待秒数与最多等待次数
RATE_LIMIT_WAIT = 60.0
RATE_LIMIT_RETRIES = 3
# 其他异常：主循环结束后间隔该秒数再试一轮
RETRY_DELAY = 2.0


class FinReportCollectTask(BaseCollectTask):
    """利润表采集（按股票维度单元）"""

    name = "fin_report"
    facet = "fundamental"
    sub_facet = "report"
    label = "季报财务"
    description = "利润表：营收 / 净利润 / EPS（tushare income，合并报表），面板净利润率数据来源"

    async def estimate_total(self, params: dict) -> int:
        return len(await self._symbols(params))

    async def run(self, params: dict, on_unit_done) -> TaskSummary:
        symbols = await self._symbols(params)
        start_date = self._start_date(params)
        fetcher: FinReportFetcher = get_registry().get(FinReportFetcher)
        logger.info("FinReport 任务 %d 启动: %d 只股票, 公告日 >= %s", self._task_id, len(symbols), start_date)

        success = fail = skip = saved_total = 0
        pending: list[str] = []

        async def work(symbol: str) -> UnitResult:
            bos = await self._fetch_with_rate_limit(fetcher, symbol, start_date)
            if not bos:
                return UnitResult(success=True, skipped=True, detail=symbol)
            async with AsyncSessionLocal() as session:
                saved = await FinReportRepoImpl(session).save_batch([b.to_entity() for b in bos])
            return UnitResult(success=True, detail=symbol, saved_count=saved)

        async def report(symbol: str, result: UnitResult) -> None:
            nonlocal success, fail, skip, saved_total
            if result.success:
                success += 1
                saved_total += result.saved_count
                skip += 1 if result.skipped else 0
            else:
                fail += 1
            await on_unit_done(result, symbol)

        for symbol in symbols:
            self._check_cancel()
            try:
                result = await work(symbol)
            except Cancelled:
                raise
            except Exception as e:
                logger.debug("财报 %s 失败，稍后重试: %s", symbol, e)
                pending.append(symbol)
                continue
            await report(symbol, result)

        for symbol in pending:
            self._check_cancel()
            await asyncio.sleep(RETRY_DELAY)
            try:
                result = await work(symbol)
            except Cancelled:
                raise
            except Exception as e:
                logger.warning("财报 %s 重试仍失败: %s", symbol, str(e)[:200])
                result = UnitResult(success=False, detail=symbol, error=str(e)[:500])
            await report(symbol, result)

        return TaskSummary(
            success=success,
            fail=fail,
            skip=skip,
            total_count=len(symbols),
            message=f"完成: 股票 {success}（无财报 {skip}），失败 {fail}；写入报告期 {saved_total} 条",
        )

    # ── helper ────────────────────────────────────────────────────────

    def _check_cancel(self) -> None:
        if is_cancelled(self._task_id):
            raise Cancelled()

    async def _fetch_with_rate_limit(
        self, fetcher: FinReportFetcher, symbol: str, start_date: Optional[str],
    ) -> list:
        ts_code = symbol_to_ts_code(symbol)
        for attempt in range(RATE_LIMIT_RETRIES + 1):
            try:
                return await asyncio.to_thread(fetcher.fetch_income, ts_code, start_date)
            except RateLimitError:
                if attempt == RATE_LIMIT_RETRIES:
                    raise
                logger.info("Tushare income 限频，等待 %.0fs 后重试 %s", RATE_LIMIT_WAIT, symbol)
                await self._sleep_cancellable(RATE_LIMIT_WAIT)
        return []

    async def _sleep_cancellable(self, seconds: float) -> None:
        remaining = seconds
        while remaining > 0:
            self._check_cancel()
            step = min(1.0, remaining)
            await asyncio.sleep(step)
            remaining -= step

    @staticmethod
    def _start_date(params: dict) -> Optional[str]:
        years = params.get("years", 1)
        if not years:
            return None
        return (date.today() - timedelta(days=int(float(years) * 365))).strftime("%Y%m%d")

    @staticmethod
    async def _symbols(params: dict) -> list[str]:
        if params.get("symbol"):
            return [str(params["symbol"]).zfill(6)]
        async with AsyncSessionLocal() as session:
            rows = await session.execute(
                select(StockInfoDB.symbol)
                .where(StockInfoDB.list_status == "L")
                .order_by(StockInfoDB.symbol)
            )
            symbols = [r[0] for r in rows.all()]
            if params.get("only_missing"):
                existing = await FinReportRepoImpl(session).list_symbols_with_reports()
                symbols = [s for s in symbols if s not in existing]
        limit = params.get("limit")
        return symbols[: int(limit)] if limit else symbols
