"""Redis + 采集限流（三合一：client 构造 + 进程内单例 + 滑动窗口 check）。"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

import redis.asyncio as aioredis

from core.config import get_settings

logger = logging.getLogger(__name__)

MAX_CONNECTIONS = 20

TUSHARE_LIMIT_KEY = "collect:rl:tushare"
ADATA_LIMIT_KEY = "collect:rl:adata"


def _build_client() -> aioredis.Redis:
    """按当前配置构建一个新的 Redis 客户端（含连接池）"""
    settings = get_settings()
    return aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_keepalive=True,  # 避免远端 Redis 主动断开空闲连接导致 10054
        socket_timeout=5,
        socket_connect_timeout=5,
        health_check_interval=30,  # 30s 一次 PING，失败自动重建
        retry_on_timeout=True,
        retry_on_error=[ConnectionError, TimeoutError],
        max_connections=MAX_CONNECTIONS,  # 防止被滥用拖垮 Redis 服务端
    )


_redis: aioredis.Redis | None = None
_init_lock: asyncio.Lock | None = None


async def get_redis() -> aioredis.Redis:
    """获取全局 Redis 单例（事件循环内 lazy 初始化）"""
    global _redis, _init_lock
    if _redis is None:
        if _init_lock is None:
            _init_lock = asyncio.Lock()
        async with _init_lock:
            if _redis is None:  # double-check
                _redis = _build_client()
                logger.info("Redis 客户端初始化完成")
    return _redis


async def close_redis() -> None:
    """关闭全局 Redis 客户端（lifespan 关闭阶段调用）"""
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None


def fetch_key_for_source(source: str) -> str:
    """数据源名 → 限流键"""
    return TUSHARE_LIMIT_KEY if source == "tushare" else ADATA_LIMIT_KEY


async def check_rate_limit(key: str, max_count: int, window_seconds: int) -> tuple[bool, int]:
    """原子限流：INCR + （首次）EXPIRE。返回 (allowed, remaining)。

    ⚠️ ★ 之前每次调用都 `INCR` + `EXPIRE window` → **每次都把窗口 TTL 重置回 60s**。
       在持续请求下（采集器一直在调），键永不过期 → 计数器**只增不减** → 永久限流。
       实测：日 K 采集时计数卡在 235 不再增长、任务永远跑不完。
    → 修正：**只在窗口第一次创建时**（count == 1）设置 EXPIRE，
      之后只 INCR，TTL 自然倒数到 0 → 窗口按预期重置。
    """
    redis = await get_redis()
    count = await redis.incr(key)
    if count == 1:
        # 窗口首开：设定存活期（用 SET NX EX 原子化，避免 INCR 已成功但 EXPIRE 失败）
        await redis.expire(key, window_seconds)
    remaining = max(0, max_count - count)
    return count <= max_count, remaining


async def check(rate_limit: Optional[tuple]) -> None:
    """业务策略：命中限流就等到窗口真正重置。None 表示不限流。

    Args:
        rate_limit: (source, max_count, window)；如 ("tushare", 200, 60)

    ⚠️ 之前固定 sleep 一个完整 window（60s）→ 窗口其实可能只剩 1s 就重置，
       白等 59s；并发时更糟：N 个 worker 各自 sleep 60s，
       醒来时计数器又被彼此推高 → **集体卡死在限流里**（实测日 K 采集即栽在这）。
       → 改为：读 Redis 里的真实 TTL，睡到窗口真正归零。
    """
    if rate_limit is None:
        return
    declared_source, max_count, window = rate_limit
    key = fetch_key_for_source(declared_source)
    allowed, _ = await check_rate_limit(key, max_count, window)
    if allowed:
        return

    # 窗口已满 → 等到 TTL 归零（而不是盲目等满 window）
    wait = window
    try:
        redis = await get_redis()
        ttl = await redis.ttl(key)
        if ttl is not None and 0 < ttl <= window:
            wait = ttl
    except Exception:
        pass

    logger.debug("限流命中: %s, 等待 %ds", declared_source, wait)
    await asyncio.sleep(wait)

    # 窗口归零后可能仍超限（并发 worker 同一时刻醒来）→ 再让一个窗口，
    # 保证醒来时一定拿到配额。
    count, _ = await check_rate_limit(key, max_count, window)
    if count > max_count:
        await asyncio.sleep(window)


__all__ = ["MAX_CONNECTIONS", "TUSHARE_LIMIT_KEY", "ADATA_LIMIT_KEY",
           "_build_client", "get_redis", "close_redis",
           "fetch_key_for_source", "check_rate_limit", "check"]
