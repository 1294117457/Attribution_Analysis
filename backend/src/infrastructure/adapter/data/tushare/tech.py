"""Tushare 技术面 Adapter：日 K"""
from __future__ import annotations

import logging
from datetime import timedelta

from application.port.data.base import DataError
from application.port.data.tech import DailyKlineParams, DailyKlinePort, KlineBO
from infrastructure.adapter.data.tushare.base import TushareAdapterBase
from infrastructure.adapter.data.tushare.client import TushareClient
from infrastructure.adapter.data.tushare.parser import TushareKlineParser, rows, symbol_to_ts_code

logger = logging.getLogger(__name__)

# 起始日往前多取 2 天，覆盖周末 / 节假日造成的首日缺口
START_BUFFER_DAYS = 2


class TushareDailyKlineAdapter(DailyKlinePort, TushareAdapterBase):
    def __init__(self, client: TushareClient) -> None:
        super().__init__(client)
        self._parser = TushareKlineParser()
        self._names: dict[str, str] = {}
        self._names_loaded = False

    async def fetch(self, p: DailyKlineParams) -> list[KlineBO]:
        ts_code = symbol_to_ts_code(p.symbol)
        buf_start = p.start_date - timedelta(days=START_BUFFER_DAYS)
        df = await self._c.query(
            "daily",
            ts_code=ts_code,
            start_date=buf_start.strftime("%Y%m%d"),
            end_date=p.end_date.strftime("%Y%m%d"),
        )
        if df.empty:
            return []
        df = df.sort_values("trade_date").reset_index(drop=True)
        klines = self._parser.parse(df, p.symbol)
        name = await self._resolve_name(p.symbol, ts_code)
        if name:
            for k in klines:
                k.name = name
        return klines

    async def _resolve_name(self, symbol: str, ts_code: str) -> str:
        """名称缓存：首次未命中时一次拉全部上市股票名称；仍未命中再单只查询"""
        if symbol in self._names:
            return self._names[symbol]
        try:
            if not self._names_loaded:
                self._names_loaded = True
                for r in rows(await self._c.query("stock_basic", list_status="L", fields="symbol,name")):
                    if r.get("symbol") and r.get("name"):
                        self._names[str(r["symbol"]).zfill(6)] = str(r["name"])
                if symbol in self._names:
                    return self._names[symbol]
            for r in rows(await self._c.query("stock_basic", ts_code=ts_code, fields="ts_code,name")):
                self._names[symbol] = str(r["name"])
                return self._names[symbol]
        except DataError as e:
            logger.warning("查询股票名称失败 %s: %r", symbol, e)
        return ""


__all__ = ["TushareDailyKlineAdapter"]
