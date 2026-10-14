"""AdataClient：同步 SDK 转异步 + 错误翻译

adata 被同花顺限流时部分接口 `return Exception(...)` 而不是 raise —— 这里统一识别为 RateLimited。
限速、重试由横向装饰器负责（03）。
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable

from contexts.data.application.port.base import RateLimited, SourceUnavailable

# 同花顺限流通常几秒内恢复（原 RETRY_BACKOFF 最长 3s）
THROTTLED_RETRY_AFTER = 3.0


class AdataClient:
    def __init__(self) -> None:
        try:
            import adata
        except ImportError as e:
            raise RuntimeError("adata 未安装：pip install adata==2.9.5") from e
        self.sdk = adata

    async def call(self, fn: Callable[[], Any], label: str = "") -> Any:
        try:
            result = await asyncio.to_thread(fn)
        except Exception as e:
            raise SourceUnavailable(f"adata.{label}: {e!r}") from e
        if isinstance(result, Exception):
            raise RateLimited(f"adata.{label}: {result!r}", retry_after=THROTTLED_RETRY_AFTER)
        return result


__all__ = ["AdataClient"]
