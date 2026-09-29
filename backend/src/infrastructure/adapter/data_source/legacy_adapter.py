"""老 Protocol → 新 KlineAPI 适配器

让路由层和 service 层继续用 KlineFetcher / StockBasicFetcher / DailyBasicFetcher /
FinReportFetcher / MinuteKlineFetcher / ConceptFetcher 等老协议，
但内部调用走新 DataSourceAPI。

设计要点：
  - 每个老 fetcher 类都重新实现对应的 Protocol
  - 内部持有一个 DataSourceAPI 实例
  - 把老协议的 fetch(params) / fetch_xxx() 签名转成新 KlineAPI.fetch_xxx(业务参数)
  - 返回值仍然是 BO 列表（service 层期望的）

这样上层代码不动，但底层全走新统一 API。
"""

from __future__ import annotations

import logging
from typing import Any

from application.port.collector_port import (
    ConceptFetcher,
    DailyBasicFetcher,
    FinReportFetcher,
    KlineFetcher,
    MinuteKlineFetcher,
    RateLimitError,
    StockBasicFetcher,
)
from application.port.data_source_api import (
    AuthError,
    CallResult,
    ConceptAPI,
    DailyBasicAPI,
    DataSourceError,
    FinReportAPI,
    KlineAPI,
    MinuteKlineAPI,
    NetworkError,
    RateLimitError as NewRateLimitError,
    StockBasicAPI,
)

logger = logging.getLogger(__name__)


def _convert_error(e: str | None, error_type: str | None) -> Exception | None:
    """CallResult.error → 老异常类型"""
    if e is None:
        return None
    if error_type == "rate_limited":
        return RateLimitError(e)
    if error_type == "auth":
        return RuntimeError(f"Auth error: {e}")
    if error_type == "network":
        return RuntimeError(f"Network error: {e}")
    return RuntimeError(e)


def _unwrap(result: CallResult) -> Any:
    """CallResult → 数据（失败时 raise 老异常）"""
    if result.ok:
        return result.data
    err = _convert_error(result.error, result.error_type)
    if err is not None:
        raise err
    raise RuntimeError(result.error or "Unknown error")


# ═══════════════════════════════════════════════════════════════════════
# TushareFetcher 适配器
# ═══════════════════════════════════════════════════════════════════════


class TushareAdapter(KlineFetcher, DailyBasicFetcher, StockBasicFetcher, FinReportFetcher):
    """Tushare 数据源适配器

    持有一个 KlineAPI 实例，实现 4 个老 Protocol。
    """

    @property
    def source_name(self) -> str:
        return self._kline_api.source_name

    def __init__(self, kline_api) -> None:
        # kline_api 必须实现 KlineAPI / DailyBasicAPI / StockBasicAPI / FinReportAPI
        self._kline_api = kline_api

    def fetch(self, params) -> list:
        """K 线采集（老协议签名 fetch(CollectParams)）"""
        # 老协议直接调同步方法（在 service 层用 asyncio.to_thread 包）
        symbol = params.symbol
        days = params.days or 30
        result: CallResult = self._do_fetch_kline_sync(symbol, days, params)
        return _unwrap(result)

    def _do_fetch_kline_sync(self, symbol: str, days: int, params) -> CallResult:
        """同步获取 CallResult（service 层用 to_thread 包）"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 在异步上下文里，直接 await 已有 loop
                # 但这里不好做，返回一个 sync wrapper
                return self._run_async(self._kline_api.fetch_kline(symbol=symbol, days=days))
            return loop.run_until_complete(
                self._kline_api.fetch_kline(symbol=symbol, days=days)
            )
        except RuntimeError:
            # 没有 event loop
            return self._run_async(self._kline_api.fetch_kline(symbol=symbol, days=days))

    @staticmethod
    def _run_async(coro):
        """在同步上下文跑异步 coroutine"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 已经在 async 里，用 run_in_executor 跑 sync method
                raise RuntimeError("Cannot run async inside running loop")
            return loop.run_until_complete(coro)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

    def fetch_stock_basic(self, params) -> list:
        list_status = (params.list_status or "L").upper()
        result = self._run_async(
            self._kline_api.fetch_stock_basic(list_status=list_status)
        )
        return _unwrap(result)

    def fetch_daily_basic(self, trade_date: str) -> list:
        result = self._run_async(
            self._kline_api.fetch_daily_basic(trade_date=trade_date)
        )
        return _unwrap(result)

    def fetch_income(self, ts_code: str, start_date=None, end_date=None) -> list:
        result = self._run_async(
            self._kline_api.fetch_income(
                ts_code=ts_code, start_date=start_date, end_date=end_date
            )
        )
        return _unwrap(result)


# ═══════════════════════════════════════════════════════════════════════
# PytdxAdapter
# ═══════════════════════════════════════════════════════════════════════


class PytdxAdapter(MinuteKlineFetcher):
    """Pytdx 数据源适配器（实现 MinuteKlineFetcher 协议）"""

    @property
    def source_name(self) -> str:
        return self._minute_api.source_name

    def __init__(self, minute_api) -> None:
        self._minute_api = minute_api

    async def fetch_minute_klines(
        self,
        symbol: str,
        interval: str = "5min",
        count: int = 800,
        name: str = "",
    ) -> list:
        result = await self._minute_api.fetch_minute_klines(
            symbol=symbol, interval=interval, count=count
        )
        return _unwrap(result)


# ═══════════════════════════════════════════════════════════════════════
# AdataAdapter
# ═══════════════════════════════════════════════════════════════════════


class AdataAdapter(ConceptFetcher):
    """Adata 数据源适配器（实现 ConceptFetcher 协议）"""

    @property
    def source_name(self) -> str:
        return self._concept_api.source_name if self._concept_api else "Adata-THS"

    def __init__(self, concept_api) -> None:
        self._concept_api = concept_api

    def _run(self, coro):
        """同步包装异步调用"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                raise RuntimeError("Already in event loop")
            return loop.run_until_complete(coro)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

    def fetch_concept_list(self) -> list:
        result = self._run(self._concept_api.fetch_concept_list())
        return _unwrap(result)

    def fetch_constituents(self, index_code: str, delay=None) -> list:
        result = self._run(self._concept_api.fetch_constituents(index_code=index_code))
        return _unwrap(result)

    def fetch_concepts_by_stock(self, symbol: str, delay=None) -> list:
        result = self._run(self._concept_api.fetch_concepts_by_stock(symbol=symbol))
        return _unwrap(result)

    def fetch_index_daily(self, index_code: str, concept_name: str = "", delay=None) -> list:
        result = self._run(self._concept_api.fetch_index_daily(index_code=index_code))
        return _unwrap(result)

    def fetch_current(self, index_code: str, delay=None):
        result = self._run(self._concept_api.fetch_current(index_code=index_code))
        return _unwrap(result)


__all__ = ["TushareAdapter", "PytdxAdapter", "AdataAdapter"]
