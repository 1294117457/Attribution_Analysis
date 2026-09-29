"""统一数据源适配器（L1 实现层）

设计要点：
  - 1 个文件 = 1 个数据源实现类
  - 实现类继承 DataSourceAPI + 对应业务协议
  - 每个方法都用 `async def` + `asyncio.to_thread` 包同步阻塞调用
  - 每个方法统一返回 CallResult（不靠 raise 表达错误）
  - 业务逻辑（解析、限频、重试）由内部 fetcher 处理，本层只做薄包装

L1 数据源实现类一览：
  - TushareAPI       — 4 个方法（kline / daily_basic / stock_basic / income）
  - AdataAPI         — 5 个方法（concept 族）
  - PytdxAPI         — 1 个方法（minute_klines）

加新数据源（Wind / Choice）= 写 1 个 `WindAPI` 类 + 注册一行
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, TypeVar

from application.port.data_source_api import (
    AuthError,
    CallResult,
    ConceptAPI,
    DailyBasicAPI,
    DataSourceAPI,
    DataSourceError,
    FinReportAPI,
    KlineAPI,
    MinuteKlineAPI,
    NetworkError,
    RateLimitError,
    StockBasicAPI,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ═══════════════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════════════


def _classify_error(e: Exception) -> str:
    """分类异常类型"""
    if isinstance(e, RateLimitError):
        return "rate_limited"
    if isinstance(e, AuthError):
        return "auth"
    if isinstance(e, NetworkError):
        return "network"
    return "other"


async def _async_call(
    source: str,
    fn: Callable[..., T],
    **kwargs: Any,
) -> CallResult:
    """异步包装同步调用，统一返回 CallResult

    - 同步阻塞函数放到 asyncio.to_thread 执行
    - DataSourceError 子类分类为 error_type
    - 其他 Exception 视为 other 错误
    """
    t0 = time.time()
    try:
        data = await asyncio.to_thread(fn, **kwargs)
        elapsed = int((time.time() - t0) * 1000)
        return CallResult.success(data=data, source=source, elapsed_ms=elapsed)
    except DataSourceError as e:
        elapsed = int((time.time() - t0) * 1000)
        return CallResult.failure(
            error=str(e),
            source=source,
            error_type=_classify_error(e),
            elapsed_ms=elapsed,
        )
    except Exception as e:
        elapsed = int((time.time() - t0) * 1000)
        logger.warning("[%s] 调用异常: %s", source, e)
        return CallResult.failure(
            error=str(e),
            source=source,
            error_type="other",
            elapsed_ms=elapsed,
        )


# ═══════════════════════════════════════════════════════════════════════
# TushareAPI
# ═══════════════════════════════════════════════════════════════════════


class TushareAPI(DataSourceAPI, KlineAPI, DailyBasicAPI, StockBasicAPI, FinReportAPI):
    """Tushare 数据源实现

    实现 KlineAPI / DailyBasicAPI / StockBasicAPI / FinReportAPI 4 个业务协议。
    所有方法 async def，内部用 asyncio.to_thread 包同步阻塞调用。
    所有方法返回 CallResult，不 raise。
    """

    source_name = "Tushare"

    def __init__(self, fetcher=None) -> None:
        if fetcher is None:
            # 延迟导入避免未安装时影响模块加载
            from infrastructure.adapter.tushare.fetcher import TushareFetcher
            from route.dto.request.kline import KlineBO

            fetcher = TushareFetcher(KlineBO)
        self._fetcher = fetcher

    @property
    def available_methods(self) -> list[str]:
        return [
            "fetch_kline",
            "fetch_stock_basic",
            "fetch_daily_basic",
            "fetch_income",
        ]

    # ── KlineAPI 实现 ──

    async def fetch_kline(self, symbol: str, days: int = 30) -> CallResult:
        from application.port.collector_port import CollectParams

        return await _async_call(
            self.source_name,
            self._fetcher.fetch,
            params=CollectParams(symbol=symbol, days=days),
        )

    # ── DailyBasicAPI 实现 ──

    async def fetch_daily_basic(self, trade_date: str) -> CallResult:
        return await _async_call(
            self.source_name,
            self._fetcher.fetch_daily_basic,
            trade_date=trade_date,
        )

    # ── StockBasicAPI 实现 ──

    async def fetch_stock_basic(self, list_status: str = "L") -> CallResult:
        from application.port.collector_port import CollectParams

        return await _async_call(
            self.source_name,
            self._fetcher.fetch_stock_basic,
            params=CollectParams(list_status=list_status),
        )

    # ── FinReportAPI 实现 ──

    async def fetch_income(
        self,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> CallResult:
        return await _async_call(
            self.source_name,
            self._fetcher.fetch_income,
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
        )


# ═══════════════════════════════════════════════════════════════════════
# AdataAPI
# ═══════════════════════════════════════════════════════════════════════


class AdataAPI(DataSourceAPI, ConceptAPI):
    """Adata（同花顺）数据源实现

    实现 ConceptAPI 协议，5 个方法（concept_list / constituents /
    concepts_by_stock / index_daily / current）。
    """

    source_name = "Adata-THS"

    def __init__(self, fetcher=None) -> None:
        if fetcher is None:
            try:
                from infrastructure.adapter.adata.fetcher import AdataConceptFetcher

                fetcher = AdataConceptFetcher()
            except Exception as e:
                logger.warning("AdataConceptFetcher 初始化失败: %s", e)
                fetcher = None
        self._fetcher = fetcher

    @property
    def available_methods(self) -> list[str]:
        return [
            "fetch_concept_list",
            "fetch_constituents",
            "fetch_concepts_by_stock",
            "fetch_index_daily",
            "fetch_current",
        ]

    def _check(self) -> CallResult | None:
        """检查 fetcher 是否可用"""
        if self._fetcher is None:
            return CallResult.failure(
                "Adata fetcher 不可用（adata 未安装？）",
                source=self.source_name,
                error_type="auth",
            )
        return None

    async def fetch_concept_list(self) -> CallResult:
        if err := self._check():
            return err
        return await _async_call(self.source_name, self._fetcher.fetch_concept_list)

    async def fetch_constituents(self, index_code: str) -> CallResult:
        if err := self._check():
            return err
        return await _async_call(
            self.source_name,
            self._fetcher.fetch_constituents,
            index_code=index_code,
        )

    async def fetch_concepts_by_stock(self, symbol: str) -> CallResult:
        if err := self._check():
            return err
        return await _async_call(
            self.source_name,
            self._fetcher.fetch_concepts_by_stock,
            symbol=symbol,
        )

    async def fetch_index_daily(self, index_code: str) -> CallResult:
        if err := self._check():
            return err
        return await _async_call(
            self.source_name,
            self._fetcher.fetch_index_daily,
            index_code=index_code,
        )

    async def fetch_current(self, index_code: str) -> CallResult:
        if err := self._check():
            return err
        return await _async_call(
            self.source_name,
            self._fetcher.fetch_current,
            index_code=index_code,
        )


# ═══════════════════════════════════════════════════════════════════════
# PytdxAPI
# ═══════════════════════════════════════════════════════════════════════


class PytdxAPI(DataSourceAPI, MinuteKlineAPI):
    """通达信数据源实现（仅分钟 K 线）"""

    source_name = "Pytdx"

    def __init__(self, fetcher=None) -> None:
        if fetcher is None:
            from infrastructure.adapter.pytdx.fetcher import PytdxFetcher

            fetcher = PytdxFetcher()
        self._fetcher = fetcher

    @property
    def available_methods(self) -> list[str]:
        return ["fetch_minute_klines"]

    async def fetch_minute_klines(
        self,
        symbol: str,
        interval: str = "5min",
        count: int = 800,
    ) -> CallResult:
        # PytdxFetcher.fetch_minute_klines 本身就是 async（内部用 loop.run_in_executor）
        # 直接 await 调用
        t0 = time.time()
        try:
            data = await self._fetcher.fetch_minute_klines(
                symbol=symbol, interval=interval, count=count
            )
            elapsed = int((time.time() - t0) * 1000)
            return CallResult.success(data=data, source=self.source_name, elapsed_ms=elapsed)
        except Exception as e:
            elapsed = int((time.time() - t0) * 1000)
            return CallResult.failure(
                error=str(e),
                source=self.source_name,
                error_type=_classify_error(e) if isinstance(e, DataSourceError) else "other",
                elapsed_ms=elapsed,
            )


__all__ = [
    "TushareAPI",
    "AdataAPI",
    "PytdxAPI",
]
