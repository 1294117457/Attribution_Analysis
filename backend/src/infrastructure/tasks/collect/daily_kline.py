"""日 K 线全量采集任务

迁移自 route/api/v1/collect_task.py::_collect_daily_kline
保留原行为：按 symbol 维度单元，并发池 + chunk 调度。

配套设计文档：docs/dev/07collect-class/01-collect-task-class-design.md §5.1
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date

from sqlalchemy import func, select

from application.dto.kline import KlineCollectRequest
from application.kline_service import KlineAppService
from infrastructure.collectors import get_registry
from infrastructure.collectors.protocols import KlineFetcher
from infrastructure.config import get_settings
from infrastructure.database.connection import AsyncSessionLocal
from infrastructure.database.models.stock_info import StockInfoDB
from infrastructure.tasks.collect.base import (
    BaseCollectTask,
    TaskSummary,
    UnitResult,
)

logger = logging.getLogger(__name__)


class DailyKlineCollectTask(BaseCollectTask):
    """日 K 线全量采集（按 symbol 维度单元）"""

    name = "daily_kline"

    def __init__(self) -> None:
        super().__init__()
        self._settings = get_settings()
        self._concurrency: int = 1
        self._api_interval: float = 0.3
        self._fetcher_pool: asyncio.Queue | None = None

    # ── estimate_total ────────────────────────────────────────────────

    async def estimate_total(self, params: dict) -> int:
        """查 DB 拿 symbol 数（exchange 可选）"""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(func.count())
                .select_from(StockInfoDB)
                .where(StockInfoDB.list_status == "L")
            )
            exchange_filter = params.get("exchange") if params else None
            if exchange_filter:
                stmt = stmt.where(StockInfoDB.exchange.in_(exchange_filter))
            result = await session.execute(stmt)
            return int(result.scalar_one())

    # ── pre_execute：预热 fetcher 池 ──────────────────────────────────

    async def pre_execute(self, params: dict) -> None:
        settings = self._settings
        max_conc = settings.COLLECT_MAX_CONCURRENCY
        user_conc = params.get("concurrency", settings.COLLECT_CONCURRENCY)
        self._concurrency = max(1, min(int(user_conc), max_conc))
        # 与既有实现一致：interval 随并发成比例（避免触发 Tushare 限频）
        self._api_interval = max(0.1, self._concurrency * 0.15)

        self._fetcher_pool = asyncio.Queue()
        for _ in range(self._concurrency):
            self._fetcher_pool.put_nowait(get_registry().create(KlineFetcher))

        logger.info(
            "DailyKline 预热完成: 并发=%d, api_interval=%.2fs",
            self._concurrency, self._api_interval,
        )

    # ── run：业务主循环 ───────────────────────────────────────────────

    async def run(
        self,
        params: dict,
        on_unit_done,
    ) -> TaskSummary:
        assert self._fetcher_pool is not None, "pre_execute 未执行"

        settings = self._settings
        chunk_size = settings.COLLECT_CHUNK_SIZE

        days = params.get("days", 7)
        start_date = params.get("start_date")
        end_date = params.get("end_date")
        exchange_filter = params.get("exchange")

        # 拉取需要采集的 symbol 列表
        async with AsyncSessionLocal() as session:
            stmt = (
                select(StockInfoDB.symbol)
                .where(StockInfoDB.list_status == "L")
            )
            if exchange_filter:
                stmt = stmt.where(StockInfoDB.exchange.in_(exchange_filter))
            stmt = stmt.order_by(StockInfoDB.symbol)
            result = await session.execute(stmt)
            symbols = [r[0] for r in result.all()]

        total = len(symbols)
        exchange_desc = (
            ",".join(exchange_filter) if exchange_filter else "全部"
        )
        logger.info(
            "日K采集 %d: 共 %d 只股票 (%s), 并发=%d",
            self._task_id, total, exchange_desc, self._concurrency,
        )

        # 构造采集参数
        collect_kwargs: dict = {}
        if start_date and end_date:
            collect_kwargs["start_date"] = date(
                int(start_date[:4]), int(start_date[4:6]), int(start_date[6:8])
            )
            collect_kwargs["end_date"] = date(
                int(end_date[:4]), int(end_date[4:6]), int(end_date[6:8])
            )
        else:
            collect_kwargs["days"] = days

        sem = asyncio.Semaphore(self._concurrency)
        success = fail = 0

        async def _collect_one(symbol: str) -> UnitResult:
            """单只股票采集：成功 / 超时 / 异常三类结果"""
            async with sem:
                fetcher = await self._fetcher_pool.get()  # type: ignore[union-attr]
                try:
                    async with AsyncSessionLocal() as session:
                        svc = KlineAppService(session=session)
                        await asyncio.wait_for(
                            svc.collect(
                                KlineCollectRequest(symbol=symbol, **collect_kwargs),
                                fetcher,
                            ),
                            timeout=120,
                        )
                        await session.commit()
                    return UnitResult(success=True, detail=symbol)
                except asyncio.TimeoutError:
                    return UnitResult(
                        success=False, detail=symbol, error="timeout 120s"
                    )
                except Exception as e:
                    return UnitResult(
                        success=False, detail=symbol, error=str(e)
                    )
                finally:
                    await self._fetcher_pool.put(fetcher)  # type: ignore[union-attr]

        for i in range(0, total, chunk_size):
            chunk = symbols[i:i + chunk_size]
            results = await asyncio.gather(*[_collect_one(s) for s in chunk])

            for r, label in zip(results, chunk):
                await on_unit_done(r, label)
                if r.success:
                    success += 1
                else:
                    fail += 1

            # 块间限频（沿用既有实现）
            await asyncio.sleep(self._api_interval * len(chunk))

        return TaskSummary(
            success=success,
            fail=fail,
            total_count=total,
            message=(
                f"完成 ({exchange_desc}, 并发{self._concurrency}): "
                f"成功 {success}, 失败 {fail}"
            ),
        )
