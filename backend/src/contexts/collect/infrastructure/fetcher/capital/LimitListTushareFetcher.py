"""LimitListTushareFetcher：每日涨跌停板（Tushare limit_list_d）—— step7 重构版"""
from __future__ import annotations

import logging
from datetime import date

import pandas as pd
from pydantic import BaseModel

from contexts.collect.infrastructure.fetcher.base import BaseFetcher
from contexts.collect.infrastructure.connect.tushare_client import get_tushare_client

logger = logging.getLogger(__name__)


class LimitListTushareFetcher(BaseFetcher):
    fetcher_type = "limit_list_d_tushare"
    source = "tushare"
    label = "每日涨跌停板（Tushare）"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        trade_date: date = params.get("trade_date")
        if not trade_date:
            raise ValueError("trade_date 必填")
        df = await self._c.query("limit_list_d", trade_date=trade_date.strftime("%Y%m%d"))
        return self._parse(df)

    def _parse(self, df: pd.DataFrame) -> list[dict]:
        if df is None or df.empty:
            return []
        out = []
        for _, row in df.iterrows():
            try:
                pct = float(row.get("pct_change", 0))
                out.append({
                    "trade_date": str(row.get("trade_date", "")),
                    "symbol": str(row["ts_code"])[:6],
                    "name": str(row.get("name", "")) if pd.notna(row.get("name")) else None,
                    "close_price": float(row["close"]) if pd.notna(row.get("close")) else None,
                    "change_rate": pct if pd.notna(row.get("pct_change")) else None,
                    "limit_type": "up_limit" if pct > 0 else "down_limit",
                    "board_count": int(row["board_count"]) if pd.notna(row.get("board_count")) else 1,
                    "first_limit_time": str(row["first_limit_time"]) if pd.notna(row.get("first_limit_time")) else None,
                    "board_strength": float(row["board_strength"]) if pd.notna(row.get("board_strength")) else None,
                    "reason": str(row["reason"]) if pd.notna(row.get("reason")) else None,
                })
            except Exception as e:
                logger.warning("跳过无效 limit_list_d 行: %s", e)
        return out


__all__ = ["LimitListTushareFetcher"]
