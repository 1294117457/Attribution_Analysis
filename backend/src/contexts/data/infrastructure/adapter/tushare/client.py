"""TushareClient：连接 / 鉴权 / 同步转异步 / 错误翻译（不认识业务字段）"""
from __future__ import annotations

import asyncio
from typing import Any

import pandas as pd

from contexts.data.application.port.base import RateLimited, SourceUnavailable

RATE_LIMIT_WAIT = 60.0


def _is_rate_limit(e: Exception) -> bool:
    msg = str(e)
    return "每分钟" in msg or "最多访问" in msg or "频率" in msg


class TushareClient:
    """pro_api 每次调用都是独立 HTTP 请求，单实例可并发使用；并发度由 ThrottleDecorator 控制"""

    def __init__(self, token: str) -> None:
        if not token:
            raise RuntimeError("TUSHARE_TOKEN 未配置")
        import tushare as ts
        self._pro = ts.pro_api(token)

    async def query(self, api: str, **kwargs: Any) -> pd.DataFrame:
        """调 pro.<api>(**kwargs)；空返回空 DataFrame；限频抛 RateLimited，其它抛 SourceUnavailable"""
        try:
            df = await asyncio.to_thread(getattr(self._pro, api), **kwargs)
        except Exception as e:
            if _is_rate_limit(e):
                raise RateLimited(str(e), retry_after=RATE_LIMIT_WAIT) from e
            raise SourceUnavailable(f"tushare.{api}: {e}") from e
        return df if df is not None else pd.DataFrame()


__all__ = ["TushareClient"]
