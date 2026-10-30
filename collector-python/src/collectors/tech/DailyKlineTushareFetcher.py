"""DailyKlineTushareFetcher：日 K 线（Tushare pro.daily）—— step7 重构版

替代旧 DailyKlineTushareAdapter(DailyKlinePort, AdapterBase, TushareAdapterBase)
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from pydantic import BaseModel

from collectors.schemas import KlineBO
from collectors.base import BaseFetcher
from core.tushare_utils import (
    TushareKlineParser,
    rows,
    symbol_to_ts_code,
)
from core.tushare_client import get_tushare_client

logger = logging.getLogger(__name__)

# 起始日往前多取 2 天，覆盖周末 / 节假日造成的首日缺口
START_BUFFER_DAYS = 2


class DailyKlineTushareFetcher(BaseFetcher):
    """日 K 线 fetcher（Tushare pro.daily）"""

    fetcher_type = "daily_kline_tushare"
    source = "tushare"
    label = "日 K 线（Tushare）"
    description = "Tushare pro.daily 接口"

    def __init__(self) -> None:
        self._c = get_tushare_client()
        self._parser = TushareKlineParser()
        self._names: dict[str, str] = {}
        self._names_loaded = False

    async def fetch(
        self, *, symbol: str, start_date: date, end_date: date,
    ) -> list[BaseModel]:
        ts_code = symbol_to_ts_code(symbol)
        buf_start = start_date - timedelta(days=START_BUFFER_DAYS)
        df = await self._c.query(
            "daily",
            ts_code=ts_code,
            start_date=buf_start.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
        )
        if df.empty:
            return []
        df = df.sort_values("trade_date").reset_index(drop=True)
        klines = self._parser.parse(df, symbol)
        name = await self._resolve_name(symbol, ts_code)
        if name:
            for k in klines:
                k.name = name
        return klines

    async def fetch_by_date(
        self, *, start_date: date, end_date: date,
    ) -> list[BaseModel]:
        """★ 按日期整批采集：一次调用拿全市场当日 K 线。

        `pro.daily(trade_date=...)` 不带 ts_code 时返回**当日全市场**（5000+ 行），
        因此「一个交易日」只需 **1 次**接口调用，而不是 5000+ 次。

        ⚠️ Tushare `daily` 单次最多返回 6000 行 → 一个交易日的全市场数据
          约 5400 行，正好在限内；但**跨多日区间**会被截断，
          所以这里**逐日**调用（每个交易日 1 次），而不是一次拉整个区间。
        """
        out: list[BaseModel] = []
        names = await self._all_names()
        d = start_date
        while d <= end_date:
            df = await self._c.query("daily", trade_date=d.strftime("%Y%m%d"))
            if not df.empty:
                for k in self._parser.parse_many(df):
                    nm = names.get(k.symbol)
                    if nm:
                        k.name = nm
                    out.append(k)
            d += timedelta(days=1)
        return out

    async def _all_names(self) -> dict[str, str]:
        """全市场股票代码 → 名称（一次 stock_basic 调用，缓存复用）。"""
        if not self._names_loaded:
            self._names_loaded = True
            try:
                for r in rows(await self._c.query(
                    "stock_basic", list_status="L", fields="symbol,name"
                )):
                    if r.get("symbol") and r.get("name"):
                        self._names[str(r["symbol"]).zfill(6)] = str(r["name"])
            except Exception as e:
                logger.warning("批量查询股票名称失败: %r", e)
        return self._names

    async def _resolve_name(self, symbol: str, ts_code: str) -> str:
        if symbol in self._names:
            return self._names[symbol]
        try:
            if not self._names_loaded:
                self._names_loaded = True
                for r in rows(await self._c.query(
                    "stock_basic", list_status="L", fields="symbol,name"
                )):
                    if r.get("symbol") and r.get("name"):
                        self._names[str(r["symbol"]).zfill(6)] = str(r["name"])
                if symbol in self._names:
                    return self._names[symbol]
            for r in rows(await self._c.query(
                "stock_basic", ts_code=ts_code, fields="ts_code,name"
            )):
                self._names[symbol] = str(r["name"])
                return self._names[symbol]
        except Exception as e:
            logger.warning("查询股票名称失败 %s: %r", symbol, e)
        return ""


__all__ = ["DailyKlineTushareFetcher"]
