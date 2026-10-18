"""HsgtTop10TushareFetcher：沪深港通前 10 持仓（Tushare hsgt_top10）—— step7 重构版

返回 list[dict]（原"非 Port 标准" fetcher 不变）
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

import pandas as pd

from pydantic import BaseModel

from contexts.collect.infrastructure.fetcher.base import BaseFetcher
from contexts.collect.infrastructure.connect.tushare_client import get_tushare_client

logger = logging.getLogger(__name__)


class HsgtTop10TushareFetcher(BaseFetcher):
    fetcher_type = "hsgt_top10_tushare"
    source = "tushare"
    label = "沪深港通前 10 持仓（Tushare）"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        trade_date: date = params.get("trade_date")
        if not trade_date:
            raise ValueError("trade_date 必填")
        df = await self._c.query("hsgt_top10", trade_date=trade_date.strftime("%Y%m%d"))
        return self._parse(df)

    def _parse(self, df: pd.DataFrame) -> list[dict]:
        if df is None or df.empty:
            return []
        out = []
        for _, row in df.iterrows():
            try:
                out.append({
                    "trade_date": str(row["trade_date"]),
                    "symbol": str(row["ts_code"])[:6],
                    "holding_days": int(row["holding_days"]) if pd.notna(row.get("holding_days")) else None,
                    "share_ratio": float(row["share_ratio"]) if pd.notna(row.get("share_ratio")) else None,
                    "hold_amount": float(row["hold_amount"]) if pd.notna(row.get("hold_amount")) else None,
                    "net_amount": float(row["net_amount"]) if pd.notna(row.get("net_amount")) else None,
                })
            except Exception as e:
                logger.warning("跳过无效 hsgt_top10 行: %s", e)
        return out


__all__ = ["HsgtTop10TushareFetcher"]
