"""Adata Client（同花顺 step7 简化）

Adata 客户端单例：每个进程只 new 一次。

使用：
    from contexts.collect.infrastructure.connect.adata_client import get_adata_client
    client = get_adata_client()
    df = await client.call(lambda: client.sdk.stock.market.list_market(), label="market")
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable

# 同花顺限流通常几秒内恢复
THROTTLED_RETRY_AFTER = 3.0


class AdataClient:
    def __init__(self) -> None:
        try:
            import adata
        except ImportError as e:
            raise RuntimeError("adata 未安装：pip install adata==2.9.5") from e
        self.sdk = adata

    async def call(self, fn: Callable[[], Any], label: str = "") -> Any:
        from contexts.collect.application.service.base import (
            RateLimited,
            SourceUnavailable,
        )
        try:
            result = await asyncio.to_thread(fn)
        except Exception as e:
            raise SourceUnavailable(f"adata.{label}: {e!r}") from e
        if isinstance(result, Exception):
            raise RateLimited(f"adata.{label}: {result!r}", retry_after=THROTTLED_RETRY_AFTER)
        return result


# ═══════════════════════════════════════════════════════════════
# 模块级单例
# ═══════════════════════════════════════════════════════════════

_adata_client: AdataClient | None = None


def get_adata_client() -> AdataClient:
    """获取 Adata 客户端单例（lazy init）"""
    global _adata_client
    if _adata_client is None:
        _adata_client = AdataClient()
    return _adata_client


__all__ = ["AdataClient", "get_adata_client"]
