"""横向装饰器：Metrics / Retry / Throttle

装配顺序：MetricsDecorator → RetryDecorator → ThrottleDecorator → XxxAdapter
- Metrics 在最外层：一次调用（含内部重试）只记一次，耗时包含等待时间
- Retry 在 Throttle 外面：每次重试都重新排队拿令牌，不会绕过限流

单进程假设：同组限流用进程内 asyncio.Semaphore + 最小调用间隔。
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Optional

from contexts.data.application.port.base import CallPolicy, DataPort, RateLimited, SourceUnavailable
from contexts.market.domain.services.market_session import market_now
from shared.infrastructure.cache.redis_client import try_get_redis
from contexts.data.infrastructure.adapter.core.context import call_policy, sleep_cancellable

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 公共：透传 Port 元数据与实现方属性
# ═══════════════════════════════════════════════════════════════════════════════


class _Decorator:
    def __init__(self, inner: Any) -> None:
        self._inner = inner

    def __getattr__(self, item: str) -> Any:
        return getattr(self._inner, item)

    def supports(self, params: Any) -> bool:
        return self._inner.supports(params)

    async def fetch(self, params: Any) -> list:
        return await self._inner.fetch(params)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._inner!r})"


# ═══════════════════════════════════════════════════════════════════════════════
# ThrottleDecorator（同源限流）
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ThrottleConfig:
    concurrency: int
    min_interval: float = 0.0


def _throttle_groups() -> dict[str, ThrottleConfig]:
    from shared.infrastructure.config.settings import get_settings
    return {
        "tushare": ThrottleConfig(concurrency=get_settings().COLLECT_MAX_CONCURRENCY, min_interval=0.15),
        "adata:ths": ThrottleConfig(concurrency=5, min_interval=0.5),
        "tdx": ThrottleConfig(concurrency=1, min_interval=0.0),
    }


THROTTLE_GROUPS: dict[str, ThrottleConfig] = _throttle_groups()


class _GroupState:
    """一个限流分组在某个事件循环里的状态（脚本多次 asyncio.run 时互不干扰）"""

    def __init__(self, cfg: ThrottleConfig) -> None:
        self.cfg = cfg
        self.sem = asyncio.Semaphore(max(1, cfg.concurrency))
        self.lock = asyncio.Lock()
        self.next_at = 0.0

    async def wait_turn(self) -> None:
        if self.cfg.min_interval <= 0:
            return
        async with self.lock:
            now = time.monotonic()
            wait = self.next_at - now
            self.next_at = max(now, self.next_at) + self.cfg.min_interval
        if wait > 0:
            await sleep_cancellable(wait)


_group_states: dict[tuple[str, int], _GroupState] = {}


def _group_state(group: str) -> _GroupState:
    key = (group, id(asyncio.get_running_loop()))
    state = _group_states.get(key)
    if state is None:
        state = _group_states[key] = _GroupState(THROTTLE_GROUPS[group])
    return state


QUERY_FETCH_TIMEOUT = 10


class ThrottleDecorator(_Decorator):
    """COLLECT：并发上限 + 最小调用间隔；QUERY：只占并发名额、不排间隔，单次取数超时 10s"""

    async def fetch(self, params: Any) -> list:
        state = _group_state(self._inner.throttle_group)
        async with state.sem:
            if call_policy.get() is CallPolicy.COLLECT:
                await state.wait_turn()
                return await self._inner.fetch(params)
            try:
                return await asyncio.wait_for(self._inner.fetch(params), timeout=QUERY_FETCH_TIMEOUT)
            except asyncio.TimeoutError as e:
                raise SourceUnavailable(
                    f"{self._inner.name}/{self._inner.tool} 超时 {QUERY_FETCH_TIMEOUT}s"
                ) from e


# ═══════════════════════════════════════════════════════════════════════════════
# RetryDecorator（同源重试）
# ═══════════════════════════════════════════════════════════════════════════════

RATE_LIMIT_RETRIES = 3
UNAVAILABLE_BACKOFF = {
    CallPolicy.COLLECT: (1.0, 3.0),
    CallPolicy.QUERY: (0.5,),
}


class RetryDecorator(_Decorator):
    async def fetch(self, params: Any) -> list:
        policy = call_policy.get()
        backoff = UNAVAILABLE_BACKOFF[policy]
        limited = unavailable = 0
        while True:
            try:
                return await self._inner.fetch(params)
            except RateLimited as e:
                if policy is CallPolicy.QUERY or limited >= RATE_LIMIT_RETRIES:
                    raise
                limited += 1
                logger.info(
                    "%s/%s 限频，等待 %.0fs 后重试 %d/%d",
                    self._inner.name, self._inner.tool, e.retry_after, limited, RATE_LIMIT_RETRIES,
                )
                await sleep_cancellable(e.retry_after)
            except SourceUnavailable as e:
                if unavailable >= len(backoff):
                    raise
                wait = backoff[unavailable]
                unavailable += 1
                logger.debug(
                    "%s/%s 不可用，%.1fs 后重试 %d/%d: %r",
                    self._inner.name, self._inner.tool, wait, unavailable, len(backoff), e,
                )
                await sleep_cancellable(wait)


# ═══════════════════════════════════════════════════════════════════════════════
# MetricsDecorator（调用统计）
# ═══════════════════════════════════════════════════════════════════════════════

STATS_KEEP_DAYS = 7


def stats_key(port_name: str, tool: str, day: str) -> str:
    return f"ds:stats:{port_name}:{tool}:{day}"


def cache_stats_key(port_name: str, day: str) -> str:
    return stats_key(port_name, "cache", day)


class MetricsDecorator(_Decorator):
    async def fetch(self, params: Any) -> list:
        started = time.perf_counter()
        try:
            items = await self._inner.fetch(params)
        except Exception as e:
            elapsed = _elapsed_ms(started)
            logger.warning(
                "数据调用失败 port=%s tool=%s %s %dms: %r",
                self._inner.name, self._inner.tool, type(e).__name__, elapsed, e,
            )
            await self._record(elapsed, e)
            raise
        await self._record(_elapsed_ms(started), None)
        return items

    async def _record(self, elapsed_ms: int, error: Optional[Exception]) -> None:
        try:
            redis = await try_get_redis()
            if redis is None:
                return
            now = market_now()
            key = stats_key(self._inner.name, self._inner.tool, now.strftime("%Y%m%d"))
            pipe = redis.pipeline()
            pipe.hincrby(key, "calls", 1)
            pipe.hincrbyfloat(key, "latency_sum", elapsed_ms)
            if error is not None:
                pipe.hincrby(key, "errors", 1)
                if isinstance(error, RateLimited):
                    pipe.hincrby(key, "rate_limited", 1)
                pipe.hset(key, mapping={"last_error": repr(error)[:500], "last_error_at": now.isoformat()})
            pipe.expire(key, STATS_KEEP_DAYS * 86400)
            await pipe.execute()
        except Exception as e:
            logger.debug("写数据调用统计失败 %s: %s", self._inner.name, e)


async def read_stats(port_name: str, tools: list[str], days: int, with_cache: bool) -> list[dict]:
    """按天合并各实现的调用统计 + 缓存命中统计（字段与原 realtime stats 一致）"""
    redis = await try_get_redis()
    today = market_now().date()
    out: list[dict] = []
    for i in range(max(1, min(days, STATS_KEEP_DAYS))):
        day = (today - timedelta(days=i)).strftime("%Y%m%d")
        calls = errors = 0
        latency_sum = 0.0
        last_error = last_error_at = None
        hits = misses = 0
        if redis is not None:
            for tool in tools:
                h = await redis.hgetall(stats_key(port_name, tool, day))
                calls += int(h.get("calls", 0))
                errors += int(h.get("errors", 0))
                latency_sum += float(h.get("latency_sum", 0))
                at = h.get("last_error_at")
                if at and (last_error_at is None or at > last_error_at):
                    last_error, last_error_at = h.get("last_error"), at
            if with_cache:
                c = await redis.hgetall(cache_stats_key(port_name, day))
                hits, misses = int(c.get("hits", 0)), int(c.get("misses", 0))
        total = hits + misses if with_cache else calls
        out.append({
            "date": day,
            "calls": total,
            "hits": hits,
            "misses": misses if with_cache else calls,
            "errors": errors,
            "hit_rate": round(hits / total, 4) if with_cache and total else None,
            "avg_latency_ms": round(latency_sum / calls, 1) if calls else None,
            "last_error": last_error,
            "last_error_at": last_error_at,
        })
    return out


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def build_decorators(adapter: DataPort) -> Any:
    return MetricsDecorator(RetryDecorator(ThrottleDecorator(adapter)))


__all__ = [
    "MetricsDecorator",
    "RetryDecorator",
    "THROTTLE_GROUPS",
    "ThrottleConfig",
    "ThrottleDecorator",
    "build_decorators",
    "cache_stats_key",
    "read_stats",
]
