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

from shared.infrastructure.config.settings import get_settings

# 同花顺限流通常几秒内恢复
THROTTLED_RETRY_AFTER = 3.0

# 限流键：所有 adata 请求共享同一配额
RATE_LIMIT_KEY = "collect:rl:adata"


class AdataClient:
    """限流由本层统一控制（阈值见 .env ADATA_RATE_LIMIT_*）。

    注意 adata 的 SDK 把异常**作为返回值**返回（而不是抛出），
    call() 负责把这种「返回值式异常」转成 RateLimited。
    """

    def __init__(self) -> None:
        try:
            import adata
        except ImportError as e:
            raise RuntimeError("adata 未安装：pip install adata==2.9.5") from e
        self.sdk = adata

    async def _acquire(self) -> None:
        """按 .env 配置申请一次 adata 配额"""
        from contexts.collect.infrastructure.cache.rate_limit import acquire
        s = get_settings()
        await acquire(
            key=RATE_LIMIT_KEY,
            max_count=s.ADATA_RATE_LIMIT_COUNT,
            window_seconds=s.ADATA_RATE_LIMIT_WINDOW,
        )

    async def call(self, fn: Callable[[], Any], label: str = "") -> Any:
        from contexts.collect.application.service.base import (
            RateLimited,
            SourceUnavailable,
        )
        await self._acquire()
        try:
            result = await asyncio.to_thread(fn)
        except Exception as e:
            raise SourceUnavailable(f"adata.{label}: {e!r}") from e
        if isinstance(result, Exception):
            raise RateLimited(
                f"adata.{label}: {result!r}",
                retry_after=THROTTLED_RETRY_AFTER,
            )
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


__all__ = ["RATE_LIMIT_KEY", "AdataClient", "get_adata_client"]