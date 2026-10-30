"""NewsTushareFetcher：新闻快讯（Tushare news）—— step7 重构版"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pandas as pd

from pydantic import BaseModel

from collectors.base import BaseFetcher
from core.tushare_client import get_tushare_client

logger = logging.getLogger(__name__)


class NewsTushareFetcher(BaseFetcher):
    fetcher_type = "news_tushare"
    source = "tushare"
    label = "新闻快讯（Tushare）"

    def __init__(self, client: TushareClient | None = None) -> None:
        self._tushare = client or get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        minutes: int = int(params.get("minutes", 30))
        df = await self._tushare.query("news")
        if df is None or df.empty:
            return []
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return self._parse(df, cutoff)

    def _parse(self, df: pd.DataFrame, cutoff: datetime) -> list[dict]:
        out = []
        for _, row in df.iterrows():
            try:
                pub_time = datetime.fromisoformat(str(row["datetime"]).replace("Z", "+00:00"))
                if pub_time < cutoff:
                    continue
            except Exception:
                continue
            out.append({
                "published_at": pub_time.isoformat(),
                "title": str(row.get("title", "")),
                "content": str(row.get("content", "")) if pd.notna(row.get("content")) else None,
                "source": str(row.get("source", "")) if pd.notna(row.get("source")) else None,
                "url": str(row.get("url", "")) if pd.notna(row.get("url")) else None,
                "symbols": self._parse_symbols(row.get("ts_codes", "")),
                "category": self._infer_category(str(row.get("title", ""))),
            })
        return out

    @staticmethod
    def _parse_symbols(codes) -> list[str]:
        if not codes:
            return []
        if isinstance(codes, list):
            return [str(c)[:6] for c in codes if c]
        if isinstance(codes, str):
            return [c.strip()[:6] for c in codes.split(",") if c.strip()]
        return []

    @staticmethod
    def _infer_category(title: str) -> str:
        t = title.lower()
        if any(k in t for k in ["涨", "涨停", "突破", "增持", "买入", "利好", "业绩增长", "超预期"]):
            return "利好"
        if any(k in t for k in ["跌", "跌停", "减持", "卖出", "利空", "业绩下滑", "预警", "风险"]):
            return "利空"
        return "中性"


__all__ = ["NewsTushareFetcher"]
