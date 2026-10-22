"""DailyTushareFetcher：日 K 线（Tushare pro.daily）—— step7 重构版

替代旧 DailyKlineTushareAdapter(DailyKlinePort, AdapterBase, TushareAdapterBase)

命名规则：<业务概念><数据源><Fetcher>
- 业务概念 Daily = 日 K 线（tech/ 下唯一，剥 Kline 不歧义）
- 数据源 Tushare
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from pydantic import BaseModel

from contexts.market.application.bo.kline import KlineBO
from contexts.collect.infrastructure.fetcher.base import BaseFetcher
from contexts.collect.infrastructure.parser.tushare import (
    TushareKlineParser,
    rows,
    symbol_to_ts_code,
)
from contexts.collect.infrastructure.connect.tushare_client import get_tushare_client

logger = logging.getLogger(__name__)

# 起始日往前多取 2 天，覆盖周末 / 节假日造成的首日缺口
START_BUFFER_DAYS = 2


class DailyTushareFetcher(BaseFetcher):
    """日 K 线 fetcher（Tushare pro.daily）"""

    fetcher_type = "daily_kline_tushare"  # 保持稳定：URL/service_name 用
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


__all__ = ["DailyTushareFetcher"]
