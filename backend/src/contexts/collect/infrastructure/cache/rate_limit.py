"""限流工具（Redis 固定窗口计数器）

纯通用原语，不认识任何数据源。阈值和 key 全部由调用方传入 —— 限流策略
下沉到 client 层，client 自己读 settings 决定用哪组配置：

    from contexts.collect.infrastructure.cache.rate_limit import acquire
    await acquire(
        key="collect:rl:tushare",
        max_count=settings.TUSHARE_RATE_LIMIT_COUNT,
        window_seconds=settings.TUSHARE_RATE_LIMIT_WINDOW,
    )

行为：
  - Lua 脚本原子执行：INCR，仅在窗口首次创建时设 EXPIRE
  - 超限时按 key 的剩余 TTL 等待，再重新检查，直到真的拿到配额才返回
    （既不丢请求，也不会像"睡满整个 window"那样把请求全推成同一时刻发出）

同一数据源的所有 service 共用一个 key → 共享配额（官方配额是账号级的）。

★ 为什么 TTL 只在首次创建时设置
    每次 INCR 都重置 EXPIRE 会让窗口变成「滑动」的：持续超压时 TTL 永不到期，
    计数无限增长，所有请求永久卡死。固定窗口必须让 TTL 自然到期。
"""
from __future__ import annotations

import asyncio
import logging

from shared.infrastructure.connection.redis_client import redis as redis_client

logger = logging.getLogger(__name__)

# 原子计数 + 仅首次设 TTL，返回当前窗口的计数
# KEYS[1]=限流键  ARGV[1]=窗口秒数
_LUA_TICK = """
local n = redis.call('INCR', KEYS[1])
if n == 1 then
    redis.call('EXPIRE', KEYS[1], tonumber(ARGV[1]))
end
return n
"""


async def acquire(
    key: str,
    max_count: int,
    window_seconds: int,
) -> None:
    """获取一次配额；超限则等到窗口腾出位置为止。

    Args:
        key: 限流键（同一数据源共用一个 key → 共享配额）
        max_count: 窗口内允许的最大请求数；<= 0 表示不限流
        window_seconds: 窗口秒数
    """
    if max_count <= 0:
        return

    while True:
        # ★ 全局单例直连，无需 await get_redis()
        count = await redis_client.eval(_LUA_TICK, 1, key, window_seconds)

        if count <= max_count:
            return

        # 超限：等当前窗口自然结束（TTL 只在窗口创建时设过一次）
        ttl = await redis_client.ttl(key)
        wait = max(1, ttl if ttl and ttl > 0 else window_seconds)
        logger.debug(
            "限流命中: %s (%d/%d), 等待 %ds",
            key, count, max_count, wait,
        )
        await asyncio.sleep(wait)


__all__ = ["acquire"]