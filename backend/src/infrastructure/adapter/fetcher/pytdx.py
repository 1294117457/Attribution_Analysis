"""通达信分钟 K 线采集器（实现 MinuteKlineFetcher 协议）

使用 pytdx 连接通达信公网行情服务器获取分钟级 K 线数据。
与 TushareFetcher 并列，独立负责分 K 采集。

模块结构（fetcher + parser 共生）：
- MinuteKlineBO       业务对象（采集层视图）
- PytdxKlineParser    数据源字段 → BO 翻译层
- PytdxFetcher        采集器主类
"""

from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime
from typing import Optional

import pandas as pd
from pydantic import BaseModel

from infrastructure.adapter.fetcher.base import BaseCollector

logger = logging.getLogger(__name__)

_INTERVAL_MAP = {
    "1min": 7,
    "5min": 0,
    "15min": 1,
    "30min": 2,
    "60min": 3,
}

_TDX_HOSTS = [
    ("jstdx.gtjas.com", 7709),
    ("shtdx.gtjas.com", 7709),
    ("sztdx.gtjas.com", 7709),
    ("180.153.18.170", 7709),
    ("60.12.136.250", 7709),
    ("115.238.56.198", 7709),
    ("218.75.126.9", 7709),
    ("119.147.212.81", 7709),
]


# ═══════════════════════════════════════════════════════════════
# 业务对象（BO）
# ═══════════════════════════════════════════════════════════════


class MinuteKlineBO(BaseModel):
    """分钟 K 线业务对象（采集层直接输出）"""

    symbol: str
    name: str = ""
    dt: datetime
    interval: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float


# ═══════════════════════════════════════════════════════════════
# Parser（数据源字段 → BO）
# ═══════════════════════════════════════════════════════════════


class PytdxKlineParser:
    """将 pytdx get_security_bars 返回的 DataFrame 转为 MinuteKlineBO 列表"""

    @staticmethod
    def parse(
        df: pd.DataFrame,
        symbol: str,
        interval: str,
        name: str = "",
    ) -> list[MinuteKlineBO]:
        if df is None or df.empty:
            return []

        results: list[MinuteKlineBO] = []
        for _, row in df.iterrows():
            try:
                bo = PytdxKlineParser._parse_row(row, symbol, interval, name)
                if bo:
                    results.append(bo)
            except Exception as e:
                logger.warning("跳过无效分钟K线行: %s", e)

        return results

    @staticmethod
    def _parse_row(
        row: pd.Series,
        symbol: str,
        interval: str,
        name: str,
    ) -> Optional[MinuteKlineBO]:
        dt_str = row.get("datetime")
        if not dt_str:
            return None

        dt = datetime.strptime(str(dt_str), "%Y-%m-%d %H:%M")

        open_val = float(row.get("open", 0))
        high_val = float(row.get("high", 0))
        low_val = float(row.get("low", 0))
        close_val = float(row.get("close", 0))
        volume = int(row.get("vol", 0))
        amount = float(row.get("amount", 0))

        if close_val <= 0:
            return None

        return MinuteKlineBO(
            symbol=symbol,
            name=name,
            dt=dt,
            interval=interval,
            open=open_val,
            high=high_val,
            low=low_val,
            close=close_val,
            volume=volume,
            amount=amount,
        )


# ═══════════════════════════════════════════════════════════════
# Fetcher（采集器主类）
# ═══════════════════════════════════════════════════════════════


class PytdxFetcher(BaseCollector):
    """通达信分钟 K 线采集器"""

    SOURCE_NAME = "Pytdx"

    def __init__(self):
        super().__init__()
        self._api = None
        self._connected = False
        # TdxHq_API 单连接非线程安全，run_in_executor 并发调用必须串行
        self._lock = threading.Lock()

    def _get_api(self):
        if self._api is None:
            from tdxpy.hq import TdxHq_API
            self._api = TdxHq_API(heartbeat=True, auto_retry=True)
        return self._api

    def _ensure_connected(self):
        """确保已连接，断线则重连"""
        api = self._get_api()
        if self._connected:
            try:
                result = api.get_security_count(0)
                if result is not None:
                    return
            except Exception:
                pass
            self._connected = False
            self._log("info", "通达信连接已断开，尝试重连...")

        for host, port in _TDX_HOSTS:
            try:
                if api.connect(host, port, time_out=5):
                    self._connected = True
                    self._log("info", f"连接通达信服务器成功: {host}:{port}")
                    return
            except Exception as e:
                self._log("warning", f"连接 {host}:{port} 失败: {e}")
        raise RuntimeError("无法连接任何通达信服务器")

    @staticmethod
    def is_supported(symbol: str) -> bool:
        """北交所（8/4/92 开头）不在 pytdx 标准行情服务器中"""
        return not (symbol.startswith(("8", "4")) or symbol.startswith("92"))

    @staticmethod
    def symbol_to_market(symbol: str) -> int:
        """股票代码 → pytdx 市场代码（0=深圳 1=上海）"""
        prefix = symbol[:2]
        if prefix in ("60", "68", "11", "51"):
            return 1
        return 0

    def _fetch_sync(
        self,
        symbol: str,
        interval: str,
        count: int,
        name: str,
    ) -> list[MinuteKlineBO]:
        """同步方法：实际拉取逻辑"""
        category = _INTERVAL_MAP.get(interval)
        if category is None:
            raise ValueError(f"不支持的周期: {interval}，可选: {list(_INTERVAL_MAP.keys())}")
        if not self.is_supported(symbol):
            raise ValueError(f"{symbol} 为北交所代码，分K暂不支持")

        market = self.symbol_to_market(symbol)
        with self._lock:
            return self._fetch_locked(category, market, symbol, interval, count, name)

    def _fetch_locked(
        self, category: int, market: int, symbol: str, interval: str, count: int, name: str,
    ) -> list[MinuteKlineBO]:
        self._ensure_connected()

        api = self._get_api()
        all_bars: list = []
        start = 0

        while len(all_bars) < count:
            batch_size = min(800, count - len(all_bars))
            try:
                bars = api.get_security_bars(category, market, symbol, start, batch_size)
            except Exception as e:
                self._log("warning", f"获取分K数据失败: {e}")
                self._connected = False
                break

            if not bars:
                break
            all_bars.extend(bars)
            start += len(bars)
            if len(bars) < batch_size:
                break

        if not all_bars:
            self._log("info", f"{symbol} {interval}: 无数据")
            return []

        df = api.to_df(all_bars)
        results = PytdxKlineParser.parse(df, symbol, interval, name)
        self._log("info", f"{symbol} {interval} 采集完成，共 {len(results)} 条")
        return results

    async def fetch_minute_klines(
        self,
        symbol: str,
        interval: str = "5min",
        count: int = 800,
        name: str = "",
    ) -> list[MinuteKlineBO]:
        """异步方法：将同步 pytdx 调用放到线程池，避免阻塞事件循环"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._fetch_sync, symbol, interval, count, name,
        )

    def disconnect(self):
        with self._lock:
            if self._api and self._connected:
                try:
                    self._api.disconnect()
                except Exception:
                    pass
                self._connected = False