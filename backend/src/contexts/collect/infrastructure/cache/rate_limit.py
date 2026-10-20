"""限流（基于 Redis 滑动窗口 + collect 业务策略）

三层 API（按需使用）：

1. 原子原语 check_rate_limit(key, max, window)
    用 INCR+EXPIRE pipeline —— 任意业务都可调
2. 业务策略 check(rate_limit_tuple)
    命中限流就 sleep 一个完整 window（最简单防拒策略）
    给 collect 22 个 service 用：
        class SomeService:
            RATE_LIMIT = ("tushare", 200, 60)
            await check(self.RATE_LIMIT)

3. 数据源→key 映射 fetch_key_for_source(source)
    全局共享配额：
        TUSHARE_LIMIT_KEY = "collect:rl:tushare"   (200 / 60s)
        ADATA_LIMIT_KEY   = "collect:rl:adata"      (100 / 60s)
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional, Tuple

from shared.infrastructure.connection.redis_client import redis as redis_client

logger = logging.getLogger(__name__)

# 全局限流键（tushare / adata 各一份，所有 service 共享配额）
TUSHARE_LIMIT_KEY = "collect:rl:tushare"
ADATA_LIMIT_KEY = "collect:rl:adata"


def fetch_key_for_source(source: str) -> str:
    """数据源名 → 限流键"""
    return TUSHARE_LIMIT_KEY if source == "tushare" else ADATA_LIMIT_KEY


# ═══════════════════════════════════════════════════════════════════════════════
# 1. 原子原语：纯 Redis pipeline（与 collect 业务无关）
# ═══════════════════════════════════════════════════════════════════════════════


async def check_rate_limit(
    key: str,
    max_count: int,
    window_seconds: int,
) -> Tuple[bool, int]:
    """原子限流：INCR + EXPIRE 一次性提交。

    Returns:
        (allowed, remaining)
        - allowed   当前计数 <= max_count 时 True
        - remaining 剩余可用次数（0 表示已用尽）
    """
    # ★ 全局单例直连，无需 await get_redis()
    async with redis_client.pipeline(transaction=True) as pipe:
        await pipe.incr(key)
        await pipe.expire(key, window_seconds)
        count, _ = await pipe.execute()
    remaining = max(0, max_count - count)
    return count <= max_count, remaining


# ═══════════════════════════════════════════════════════════════════════════════
# 2. collect 业务策略：命中限流则 await 一个完整 window
# ═══════════════════════════════════════════════════════════════════════════════


async def check(
    rate_limit: Optional[tuple],
) -> None:
    """命中限流就 await 一个完整 window（同步等待）

    Args:
        rate_limit: (source, max_count, window)；None 表示不限流
            - source: 数据源名（"tushare" / "adata"）
            - max_count: 窗口内允许的最大请求数
            - window: 窗口秒数
    """
    if rate_limit is None:
        return
    declared_source, max_count, window = rate_limit
    key = fetch_key_for_source(declared_source)
    allowed, _ = await check_rate_limit(key, max_count, window)
    if not allowed:
        logger.debug("限流命中: %s, 等待 %ds", declared_source, window)
        await asyncio.sleep(window)


__all__ = [
    "ADATA_LIMIT_KEY",
    "TUSHARE_LIMIT_KEY",
    "check",
    "check_rate_limit",
    "fetch_key_for_source",
]
