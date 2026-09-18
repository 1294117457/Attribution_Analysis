"""PytdxFetcher — 通达信分钟 K 线采集器

使用 pytdx 连接通达信公网行情服务器获取分钟级 K 线数据。
与 TushareFetcher 并列，独立负责分 K 采集。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import pandas as pd

from infrastructure.collectors.base import BaseCollector
from infrastructure.collectors.pytdx.parser import PytdxKlineParser, MinuteKlineBO

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


class PytdxFetcher(BaseCollector):
    """通达信分钟 K 线采集器"""

    def __init__(self):
        super().__init__()
        self._api = None
        self._connected = False

    @property
    def source_name(self) -> str:
        return "Pytdx"

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

        market = self.symbol_to_market(symbol)
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
        if self._api and self._connected:
            try:
                self._api.disconnect()
            except Exception:
                pass
            self._connected = False
