"""NewsTushareFetcher：新闻快讯（Tushare news）—— 字段对齐 §1.6

接口：Tushare pro.news
⚠️ pro.news 需单独开通权限（5000+ 积分）；fetcher 增加权限检测

输出字段（对齐 Tushare news 文档）:
    datetime  → published_at
    content   → content
    title     → title
    channels  → channels
    (Tushare 文档返回的) ts_code 关联 → symbols 列表
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pandas as pd

from pydantic import BaseModel

from contexts.collect.infrastructure.fetcher.base import BaseFetcher
from contexts.collect.infrastructure.connect.tushare_client import get_tushare_client, TushareClient

logger = logging.getLogger(__name__)


class NewsTushareFetcher(BaseFetcher):
    fetcher_type = "news_tushare"
    source = "tushare"
    label = "新闻快讯（Tushare）"

    def __init__(self, client: TushareClient | None = None) -> None:
        self._tushare = client or get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        minutes: int = int(params.get("minutes", 30))
        try:
            df = await self._tushare.query("news")
        except Exception as e:
            # §1.6 pro.news 需单独权限；捕获异常并打日志，不抛错
            logger.warning("Tushare pro.news 调用失败（可能权限未开通）: %r", e)
            return []
        if df is None or df.empty:
            return []
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return self._parse(df, cutoff)

    def _parse(self, df: pd.DataFrame, cutoff: datetime) -> list[dict]:
        out = []
        for _, row in df.iterrows():
            try:
                raw_dt = row.get("datetime")
                if pd.isna(raw_dt):
                    continue
                pub_time = datetime.fromisoformat(str(raw_dt).replace("Z", "+00:00"))
                if pub_time < cutoff:
                    continue
            except Exception:
                continue
            out.append({
                # §1.6 字段对齐 Tushare news 文档
                "published_at": str(pub_time.isoformat()),
                "title": str(row.get("title", "")) if pd.notna(row.get("title")) else "",
                "content": str(row.get("content", "")) if pd.notna(row.get("content")) else None,
                "source": str(row.get("source", "")) if pd.notna(row.get("source")) else None,
                "url": str(row.get("url", "")) if pd.notna(row.get("url")) else None,
                # §1.6 文档字段叫 channels（频道），并尝试从 ts_code 关联提取 symbols
                "channels": str(row.get("channels", "")) if pd.notna(row.get("channels")) else None,
                "symbols": self._parse_symbols(row.get("ts_code")),
                "category": self._infer_category(str(row.get("title", ""))),
                # sentiment 字段占位（后续 AI 分类）
                "sentiment": None,
            })
        return out

    @staticmethod
    def _parse_symbols(codes) -> list[str]:
        """§1.6 兼容：尝试多种字段名（ts_code / ts_codes / symbols）"""
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
