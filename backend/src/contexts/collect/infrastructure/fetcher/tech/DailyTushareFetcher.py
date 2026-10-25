"""DailyTushareFetcher：日 K 线（Tushare pro.daily）

命名规则：<业务概念><数据源><Fetcher>
- 业务概念 Daily = 日 K 线（tech/ 下唯一，剥 Kline 不歧义）
- 数据源 Tushare

采集形态（仅两种，对应两个公开方法）：
- fetch_by_date(trade_date)            → 当日全市场
- fetch_by_ts_code(ts_code, start, end) → 单股整段区间

⚠️ 本 fetcher 不提供「全市场 + 区间」入口：pro.daily 单次响应硬上限
6000 行且静默截断（超量不报错、不告警）。区间必须由 service 层
展开成逐日调用（见 DailyService._collect_all_days）。
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from pydantic import BaseModel

from contexts.collect.infrastructure.parser.tushare import (
    TushareKlineParser,
    rows,
)
from contexts.collect.infrastructure.connect.tushare_client import get_tushare_client
from shared.interface.validators import to_ts_code

logger = logging.getLogger(__name__)

# 起始日往前多取 2 天，覆盖周末 / 节假日造成的首日缺口
START_BUFFER_DAYS = 2


class DailyTushareFetcher:
    """日 K 线 fetcher（Tushare pro.daily）

    不继承 BaseFetcher、不提供 fetch(**params) 通用入口 —— 日 K 线的采集
    形态天然二分，两个语义化方法比运行时猜参数更安全。
    """

    fetcher_type = "daily_kline_tushare"  # 保持稳定：URL/service_name 用
    source = "tushare"
    label = "日 K 线（Tushare）"
    description = "Tushare pro.daily 接口"

    def __init__(self) -> None:
        self._c = get_tushare_client()
        self._parser = TushareKlineParser()
        self._names: dict[str, str] = {}
        self._names_loaded = False

    async def fetch_by_date(self, trade_date: date) -> list[BaseModel]:
        """拉取某个交易日的全市场日 K"""
        df = await self._c.query(
            "daily",
            trade_date=trade_date.strftime("%Y%m%d"),
        )
        if df is None or df.empty:
            return []
        df = df.sort_values(["trade_date", "ts_code"]).reset_index(drop=True)
        return self._parser.parse_frame(df)

    async def fetch_by_ts_code(
        self, *, ts_code: str, start_date: date, end_date: date,
    ) -> list[BaseModel]:
        """拉取单只股票整段区间的日 K（ts_code 接受 6 位或带后缀）"""
        ts_code = to_ts_code(ts_code)
        buf_start = start_date - timedelta(days=START_BUFFER_DAYS)
        df = await self._c.query(
            "daily",
            ts_code=ts_code,
            start_date=buf_start.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
        )
        if df is None or df.empty:
            return []
        df = df.sort_values("trade_date").reset_index(drop=True)
        symbol = ts_code.split(".")[0]
        klines = self._parser.parse(df, symbol)
        name = await self._resolve_name(symbol, ts_code)
        if name:
            for k in klines:
                k.name = name
        return klines

    async def _resolve_name(self, symbol: str, ts_code: str) -> str:
        """查股票名称（带缓存，查不到返回空串）"""
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