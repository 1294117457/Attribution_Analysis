"""MoneyflowHsgtTushareFetcher：沪深港通资金流向（Tushare moneyflow_hsgt）—— step7 重构版"""
from __future__ import annotations

import logging
from datetime import date

import pandas as pd
from pydantic import BaseModel

from contexts.collect.infrastructure.fetcher.base import BaseFetcher
from contexts.collect.infrastructure.connect.tushare_client import get_tushare_client

logger = logging.getLogger(__name__)


class MoneyflowHsgtTushareFetcher(BaseFetcher):
    fetcher_type = "moneyflow_hsgt_tushare"
    source = "tushare"
    label = "沪深港通资金流向（Tushare）"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        trade_date: date | None = params.get("trade_date")
        if trade_date:
            df = await self._c.query("moneyflow_hsgt", trade_date=trade_date.strftime("%Y%m%d"))
        else:
            df = await self._c.query("moneyflow_hsgt")
        return self._parse(df)

    def _parse(self, df: pd.DataFrame) -> list[dict]:
        if df is None or df.empty:
            return []
        out = []
        for _, row in df.iterrows():
            out.append({
                "trade_date": str(row.get("trade_date", "")),
                "exchange": str(row.get("exchange", "")),
                "buy_amount": float(row["buy_amount"]) if pd.notna(row.get("buy_amount")) else None,
                "sell_amount": float(row["sell_amount"]) if pd.notna(row.get("sell_amount")) else None,
                "net_amount": float(row["net_amount"]) if pd.notna(row.get("net_amount")) else None,
            })
        return out


__all__ = ["MoneyflowHsgtTushareFetcher"]
