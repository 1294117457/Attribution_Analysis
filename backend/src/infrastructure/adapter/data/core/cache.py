"""CacheDecorator：实时类 Port 的缓存 + 单飞（位于 Gateway 选源之前）

Redis 键：
- 缓存  ds:cache:{port}:{sha1(params)}       JSON {items, source, fetched_at}，TTL 由 market_session.ttl_for 决定
- 单飞  ds:lock:{port}:{sha1(params)}        SET NX EX 5
- 统计  ds:stats:{port}:cache:{yyyymmdd}     HASH hits / misses

Redis 不可用时直接取数、不缓存。失败不写缓存、不降级（降级由应用层决定）。
单次取数超时由 ThrottleDecorator 在 QUERY 策略下控制（排队等待不计入超时）。
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Awaitable, Callable, Optional

from pydantic import BaseModel

from application.port.data.base import DataPort, DataResult
from domain.service.market_session import market_now, ttl_for
from infrastructure.adapter.cache.redis_client import try_get_redis
from infrastructure.adapter.data.core.decorators import STATS_KEEP_DAYS, cache_stats_key

logger = logging.getLogger(__name__)

LOCK_TTL = 5
LOCK_WAIT_SECONDS = 2.0
LOCK_POLL_INTERVAL = 0.1


def params_hash(params: BaseModel) -> str:
    raw = json.dumps(params.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


class CacheDecorator:
    async def get_or_load(
        self,
        port: type[DataPort],
        params: BaseModel,
        load: Callable[[], Awaitable[DataResult]],
    ) -> DataResult:
        h = params_hash(params)
        key = f"ds:cache:{port.name}:{h}"
        redis = await try_get_redis()
        if redis is None:
            return await load()

        hit = await self._read(redis, key, port)
        if hit is not None:
            await self._count(redis, port.name, hit=True)
            return hit

        lock_key: Optional[str] = f"ds:lock:{port.name}:{h}"
        if not await redis.set(lock_key, "1", nx=True, ex=LOCK_TTL):
            waited = 0.0
            while waited < LOCK_WAIT_SECONDS:
                await asyncio.sleep(LOCK_POLL_INTERVAL)
                waited += LOCK_POLL_INTERVAL
                hit = await self._read(redis, key, port)
                if hit is not None:
                    await self._count(redis, port.name, hit=True)
                    return hit
            lock_key = None

        await self._count(redis, port.name, hit=False)
        try:
            result = await load()
            await self._write(redis, key, result, ttl_for(port.cache.ttl_trading))
            return result
        finally:
            if lock_key:
                try:
                    await redis.delete(lock_key)
                except Exception:
                    pass

    @staticmethod
    async def _read(redis: Any, key: str, port: type[DataPort]) -> Optional[DataResult]:
        try:
            raw = await redis.get(key)
        except Exception:
            return None
        if raw is None:
            return None
        try:
            obj = json.loads(raw)
            fetched_at = obj.get("fetched_at")
            return DataResult(
                items=[port.Item.model_validate(i) for i in obj.get("items", [])],
                source=obj.get("source", ""),
                cached=True,
                fetched_at=datetime.fromisoformat(fetched_at) if fetched_at else None,
            )
        except Exception as e:
            logger.warning("实时缓存反序列化失败 %s: %r", key, e)
            return None

    @staticmethod
    async def _write(redis: Any, key: str, result: DataResult, ttl: int) -> None:
        payload = json.dumps({
            "items": [i.model_dump(mode="json") for i in result.items],
            "source": result.source,
            "fetched_at": (result.fetched_at or market_now()).isoformat(),
        }, ensure_ascii=False)
        try:
            await redis.set(key, payload, ex=ttl)
        except Exception as e:
            logger.warning("写实时缓存失败 %s: %s", key, e)

    @staticmethod
    async def _count(redis: Any, port_name: str, *, hit: bool) -> None:
        try:
            key = cache_stats_key(port_name, market_now().strftime("%Y%m%d"))
            pipe = redis.pipeline()
            pipe.hincrby(key, "hits" if hit else "misses", 1)
            pipe.expire(key, STATS_KEEP_DAYS * 86400)
            await pipe.execute()
        except Exception as e:
            logger.debug("写缓存统计失败 %s: %s", port_name, e)


__all__ = ["CacheDecorator", "params_hash"]
