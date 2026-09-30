"""实时接口执行入口：缓存 / 单飞 / 同源限流 / 超时 / 降级 / 统计

Redis 键：
- 缓存  rt:{name}:{cache_key}          JSON {data, fetched_at}，TTL 见 ttl_for
- 单飞  rt:lock:{name}:{cache_key}     SET NX EX 5
- 统计  rt:stats:{name}:{yyyymmdd}     HASH，保留 7 天

单进程假设：同源限流用进程内 asyncio.Semaphore。Redis 不可用时直接请求数据源，不缓存。

配套设计文档：docs/dev/step2/04采集管理优化/06实时数据接口.md §3
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Any, Optional

from infrastructure.adapter.cache.redis_client import get_redis
from infrastructure.adapter.realtime.base import BaseRealtimeQuery, market_now, ttl_for
from infrastructure.adapter.realtime.registry import get_realtime_registry

logger = logging.getLogger(__name__)

SOURCE_CONCURRENCY = {"ths": 5, "tdx": 1}
DEFAULT_CONCURRENCY = 3
FETCH_TIMEOUT = 10
LOCK_TTL = 5
LOCK_WAIT_SECONDS = 2.0
LOCK_POLL_INTERVAL = 0.1
STATS_KEEP_DAYS = 7


class RealtimeQueryError(RuntimeError):
    """数据源失败且无降级结果"""


@dataclass
class RealtimeResult:
    data: Any
    cached: bool = False
    stale: bool = False
    fetched_at: Optional[str] = None
    latency_ms: int = 0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class RealtimeAppService:
    def __init__(self) -> None:
        self._semaphores: dict[str, asyncio.Semaphore] = {}

    def get_query(self, name: str) -> BaseRealtimeQuery:
        q = get_realtime_registry().get(name)
        if q is None:
            raise KeyError(f"未知实时接口: {name}")
        return q

    async def query(self, name: str, params: dict) -> RealtimeResult:
        """单次查询；参数非法抛 ValueError，数据源失败且无降级抛 RealtimeQueryError"""
        q = self.get_query(name)
        params = q.normalize(params)
        started = time.perf_counter()
        try:
            result = await self._query(q, params)
        except Exception as e:
            await self._record(q.name, started, hit=False, error=str(e))
            raise
        await self._record(q.name, started, hit=result.cached, error=None)
        result.latency_ms = _elapsed_ms(started)
        return result

    async def query_many(self, name: str, params_list: list[dict]) -> list[RealtimeResult]:
        """批量查询；单项失败不影响其他项（该项 data=None、带 error）"""

        async def one(p: dict) -> RealtimeResult:
            try:
                return await self.query(name, p)
            except Exception as e:
                return RealtimeResult(data=None, error=str(e))

        return list(await asyncio.gather(*(one(p) for p in params_list)))

    async def stats(self, name: str, days: int = 1) -> list[dict]:
        self.get_query(name)
        redis = await get_redis()
        today = market_now().date()
        out: list[dict] = []
        for i in range(max(1, min(days, STATS_KEEP_DAYS))):
            day = (today - timedelta(days=i)).strftime("%Y%m%d")
            h = await redis.hgetall(_stats_key(name, day))
            calls = int(h.get("calls", 0))
            hits = int(h.get("hits", 0))
            out.append({
                "date": day,
                "calls": calls,
                "hits": hits,
                "misses": int(h.get("misses", 0)),
                "errors": int(h.get("errors", 0)),
                "hit_rate": round(hits / calls, 4) if calls else None,
                "avg_latency_ms": round(float(h.get("latency_sum", 0)) / calls, 1) if calls else None,
                "last_error": h.get("last_error"),
                "last_error_at": h.get("last_error_at"),
            })
        return out

    # ── 内部 ────────────────────────────────────────

    async def _query(self, q: BaseRealtimeQuery, params: dict) -> RealtimeResult:
        ck = q.cache_key(params)
        cache_key = f"rt:{q.name}:{ck}"
        redis = await _redis_or_none()

        if redis is not None:
            hit = await _read_cache(redis, cache_key)
            if hit is not None:
                return hit
            lock_key = f"rt:lock:{q.name}:{ck}"
            if not await redis.set(lock_key, "1", nx=True, ex=LOCK_TTL):
                waited = 0.0
                while waited < LOCK_WAIT_SECONDS:
                    await asyncio.sleep(LOCK_POLL_INTERVAL)
                    waited += LOCK_POLL_INTERVAL
                    hit = await _read_cache(redis, cache_key)
                    if hit is not None:
                        return hit
                lock_key = None
        else:
            lock_key = None

        try:
            try:
                data = await self._fetch(q, params)
            except Exception as e:
                logger.warning("实时接口 %s(%s) 请求失败: %s", q.name, ck, e)
                fallback = await _safe_fallback(q, params)
                if fallback is None:
                    raise RealtimeQueryError(f"{q.label or q.name} 获取失败: {e}") from e
                return RealtimeResult(data=fallback, stale=True, fetched_at=market_now().isoformat())

            fetched_at = market_now().isoformat()
            if redis is not None:
                payload = json.dumps({"data": data, "fetched_at": fetched_at}, ensure_ascii=False, default=str)
                try:
                    await redis.set(cache_key, payload, ex=ttl_for(q.ttl_trading))
                except Exception as e:
                    logger.warning("写实时缓存失败 %s: %s", cache_key, e)
            return RealtimeResult(data=data, fetched_at=fetched_at)
        finally:
            if redis is not None and lock_key:
                try:
                    await redis.delete(lock_key)
                except Exception:
                    pass

    async def _fetch(self, q: BaseRealtimeQuery, params: dict) -> Any:
        sem = self._semaphores.get(q.source)
        if sem is None:
            sem = self._semaphores[q.source] = asyncio.Semaphore(
                SOURCE_CONCURRENCY.get(q.source, DEFAULT_CONCURRENCY)
            )
        async with sem:
            return await asyncio.wait_for(q.fetch(params), timeout=FETCH_TIMEOUT)

    async def _record(self, name: str, started: float, hit: bool, error: Optional[str]) -> None:
        try:
            redis = await get_redis()
            key = _stats_key(name, market_now().strftime("%Y%m%d"))
            pipe = redis.pipeline()
            pipe.hincrby(key, "calls", 1)
            pipe.hincrby(key, "hits" if hit else "misses", 1)
            pipe.hincrbyfloat(key, "latency_sum", _elapsed_ms(started))
            if error:
                pipe.hincrby(key, "errors", 1)
                pipe.hset(key, mapping={"last_error": error[:500], "last_error_at": market_now().isoformat()})
            pipe.expire(key, STATS_KEEP_DAYS * 86400)
            await pipe.execute()
        except Exception as e:
            logger.debug("写实时统计失败 %s: %s", name, e)


def _stats_key(name: str, day: str) -> str:
    return f"rt:stats:{name}:{day}"


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


async def _redis_or_none():
    try:
        redis = await get_redis()
        await redis.ping()
        return redis
    except Exception as e:
        logger.warning("Redis 不可用，实时接口直连数据源: %s", e)
        return None


async def _read_cache(redis, key: str) -> Optional[RealtimeResult]:
    try:
        raw = await redis.get(key)
    except Exception:
        return None
    if raw is None:
        return None
    obj = json.loads(raw)
    return RealtimeResult(data=obj.get("data"), cached=True, fetched_at=obj.get("fetched_at"))


async def _safe_fallback(q: BaseRealtimeQuery, params: dict) -> Any:
    try:
        return await q.fallback(params)
    except Exception as e:
        logger.warning("实时接口 %s 降级失败: %s", q.name, e)
        return None


_service: Optional[RealtimeAppService] = None


def get_realtime_app_service() -> RealtimeAppService:
    global _service
    if _service is None:
        _service = RealtimeAppService()
    return _service
