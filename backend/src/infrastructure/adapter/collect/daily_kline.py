"""日 K 线采集任务

单元 = 1 只股票。collect_one 采单只并落库（含技术指标），业务入口
POST /klines/collect、/klines/collect/batch 与池操作经它复用。
限频 / 重试由 DataGateway 的横向装饰器负责（tushare 组并发上限 COLLECT_MAX_CONCURRENCY）。

参数：
  days                  回溯天数，默认 7
  start_date/end_date   YYYYMMDD / YYYY-MM-DD / date，同时给出时优先于 days
  exchange              交易所过滤（列表），仅批量
  symbols               指定股票列表，仅批量（不给则全部上市股票）
  concurrency           并发数，上限 COLLECT_MAX_CONCURRENCY
  mode                  full / condition（采集管理页面下发）：按库中每只股票已有的
                        日期区间裁剪采集窗口，已覆盖的股票直接跳过
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Any, Optional

from sqlalchemy import func, select

from route.dto.request.kline import KlineCollectRequest
from domain.entitys.kline.entity import CollectionError
from infrastructure.config.settings import get_settings
from infrastructure.persistence.connection import AsyncSessionLocal
from infrastructure.persistence.models.stock_info import StockInfoDB
from infrastructure.persistence.models.tech_kline import TechKlineDailyDB
from infrastructure.adapter.collect.base import (
    BaseCollectTask,
    TaskSummary,
    UnitResult,
    run_units,
)

logger = logging.getLogger(__name__)

# 限频时 RetryDecorator 最多等待 3 × 60s，单元超时需覆盖
UNIT_TIMEOUT = 300
# mode=full 且库中无数据时的起始日
FULL_START = date(2015, 1, 1)


def _parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date):
        return value
    s = str(value).replace("-", "")
    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def _last_weekday(d: date) -> date:
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def build_request(
    symbol: str,
    params: dict,
    window: Optional[tuple[date, date]] = None,
) -> KlineCollectRequest:
    if window:
        return KlineCollectRequest(
            symbol=symbol, start_date=window[0], end_date=window[1]
        )
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
        # mode 下每只股票裁剪后的采集窗口（pending_units 计算）
        self._windows: dict[str, tuple[date, date]] = {}

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

    async def pending_units(self, params: dict) -> list[str]:
        """带 mode 时按库中已有日期区间裁剪每只股票的窗口，已覆盖的跳过

        - full:      已有数据 → 从最新一天之后补到今天；无数据 → FULL_START 起
        - condition: 请求区间（不早于上市日）已被覆盖 → 跳过；
                     起点落在已有区间内 → 从最新一天之后补
        """
        symbols = await self.list_units(params)
        self._windows = {}
        mode = params.get("mode")
        if not mode:
            return symbols

        today = date.today()
        if mode == "full":
            req_start, req_end = FULL_START, today
        else:
            req_start = _parse_date(params.get("start_date"))
            req_end = _parse_date(params.get("end_date"))
            if not (req_start and req_end):
                req_end = today
                req_start = today - timedelta(days=int(params.get("days", 7)) - 1)
        last_day = _last_weekday(min(req_end, today))

        async with AsyncSessionLocal() as session:
            cov_rows = await session.execute(
                select(
                    TechKlineDailyDB.symbol,
                    func.min(TechKlineDailyDB.date),
                    func.max(TechKlineDailyDB.date),
                )
                .where(TechKlineDailyDB.symbol.in_(symbols))
                .group_by(TechKlineDailyDB.symbol)
            )
            coverage = {r[0]: (r[1], r[2]) for r in cov_rows.all()}
            list_rows = await session.execute(
                select(StockInfoDB.symbol, StockInfoDB.list_date).where(
                    StockInfoDB.symbol.in_(symbols)
                )
            )
            list_dates = {r[0]: r[1] for r in list_rows.all()}

        pending: list[str] = []
        for s in symbols:
            start = max(req_start, list_dates.get(s) or req_start)
            cov = coverage.get(s)
            if cov:
                cov_min, cov_max = cov
                if mode == "full" or cov_min <= start <= cov_max:
                    start = max(start, cov_max + timedelta(days=1))
            if start > last_day:
                continue
            self._windows[s] = (start, req_end)
            pending.append(s)
        logger.info(
            "日K %s 模式: 共 %d 只，跳过已覆盖 %d 只",
            mode,
            len(symbols),
            len(symbols) - len(pending),
        )
        return pending

    async def collect_one(self, unit: str, params: dict) -> UnitResult:
        return await self._collect_symbol(unit, params)

    async def _collect_symbol(self, symbol: str, params: dict) -> UnitResult:
        from infrastructure.config.di import build_stock_info_service

        async with AsyncSessionLocal() as session:
            try:
                svc = build_stock_info_service(session)
                window = self._windows.get(symbol) if params.get("mode") else None
                resp = await asyncio.wait_for(
                    svc.collect(build_request(symbol, params, window)),
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
            except asyncio.TimeoutError:
                logger.warning("股票 %s 采集超时 (%ds)", symbol, UNIT_TIMEOUT)
                return UnitResult(
                    success=False,
                    detail=symbol,
                    error=f"timeout {UNIT_TIMEOUT}s",
                )
            except CollectionError as e:
                logger.warning("股票 %s 采集业务异常: %s", symbol, e)
                return UnitResult(success=False, detail=symbol, error=str(e)[:500])
            except Exception as e:
                logger.error(
                    "股票 %s 采集异常: %s",
                    symbol,
                    e,
                    exc_info=True,
                )
                return UnitResult(success=False, detail=symbol, error=str(e)[:500])

    # ── 批量 ───────────────────────────────────────────────────────────

    async def pre_execute(self, params: dict) -> None:
        settings = self._settings
        user_conc = params.get("concurrency", settings.COLLECT_CONCURRENCY)
        self._concurrency = max(1, min(int(user_conc), settings.COLLECT_MAX_CONCURRENCY))

    async def run(self, params: dict, on_unit_done) -> TaskSummary:
        """单元失败不抛异常（_collect_symbol 已转成失败结果），所以不会进入 run_units 的重试轮"""
        symbols = await self.pending_units(params)
        exchange_filter = params.get("exchange")
        exchange_desc = ",".join(exchange_filter) if exchange_filter else "全部"
        logger.info(
            "日K采集 %d: 共 %d 只股票 (%s), 并发=%d",
            self._task_id, len(symbols), exchange_desc, self._concurrency,
        )

        async def work(symbol: str, _delay: Optional[float]) -> UnitResult:
            return await self._collect_symbol(symbol, params)

        tally = await run_units(
            self._task_id, symbols, str, work, on_unit_done, concurrency=self._concurrency,
        )
        return TaskSummary(
            success=tally.success,
            fail=tally.fail,
            skip=tally.skip,
            total_count=len(symbols),
            message=(
                f"完成 ({exchange_desc}, 并发{self._concurrency}): "
                f"成功 {tally.success}（无数据 {tally.skip}），失败 {tally.fail}；写入 {tally.saved} 条"
            ),
        )

