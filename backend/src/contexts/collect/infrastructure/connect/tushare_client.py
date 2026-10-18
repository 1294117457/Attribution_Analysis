"""Tushare Client（step7 简化）

Tushare 客户端单例：每个进程只 new 一次，复用内部连接池。

使用：
    from contexts.collect.infrastructure.connect.tushare_client import get_tushare_client
    client = get_tushare_client()
    df = await client.query("adj_factor", ts_code="000001.SZ")
"""
from __future__ import annotations

import asyncio
from typing import Any

import pandas as pd

from shared.infrastructure.config.settings import get_settings

RATE_LIMIT_WAIT = 60.0


def _is_rate_limit(e: Exception) -> bool:
    msg = str(e)
    return "每分钟" in msg or "最多访问" in msg or "频率" in msg


class TushareClient:
    """pro_api 每次调用都是独立 HTTP 请求，单实例可并发使用；并发度由 service CONCURRENCY 控制"""

    def __init__(self, token: str) -> None:
        if not token:
            raise RuntimeError("TUSHARE_TOKEN 未配置")
        import tushare as ts
        self._pro = ts.pro_api(token)

    async def query(self, api: str, **kwargs: Any) -> pd.DataFrame:
        """调 pro.<api>(**kwargs)；空返回空 DataFrame；限频抛 RateLimited，其它抛 SourceUnavailable"""
        from contexts.collect.application.service.base import (
            RateLimited,
            SourceUnavailable,
        )
        try:
            df = await asyncio.to_thread(getattr(self._pro, api), **kwargs)
        except Exception as e:
            if _is_rate_limit(e):
                raise RateLimited(str(e), retry_after=RATE_LIMIT_WAIT) from e
            raise SourceUnavailable(f"tushare.{api}: {e}") from e
        return df if df is not None else pd.DataFrame()


# ═══════════════════════════════════════════════════════════════
# 模块级单例（事件循环内 lazy init）
# ═══════════════════════════════════════════════════════════════

_tushare_client: TushareClient | None = None


def get_tushare_client() -> TushareClient:
    """获取 Tushare 客户端单例（lazy init）

    首次调用时根据 settings.TUSHARE_TOKEN 构造。
    后续调用返回同一实例 —— 复用 tushare 内部 HTTP 连接池。
    """
    global _tushare_client
    if _tushare_client is None:
        _tushare_client = TushareClient(get_settings().TUSHARE_TOKEN)
    return _tushare_client


__all__ = ["TushareClient", "get_tushare_client"]
