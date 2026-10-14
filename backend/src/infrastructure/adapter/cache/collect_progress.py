"""采集进度（Redis `collect:progress:{task_id}`）

key 与字段完全沿用 base._update_progress / execute_task / prepare 的旧实现：
  - init: 写 total/done/success/fail/skip/status=running/current，TTL 86400
  - set_total: 单独改 total
  - step: done++ / success 或 fail++（skip 时再 skip++）/ current=label
  - set_status: 单独改 status

配套设计文档：docs/backend-docs/dev/step5/03collect优化/02-端口与基础设施实现.md §3.2
"""
from __future__ import annotations

import logging

from application.port.collect_port import CollectProgressPort
from infrastructure.adapter.cache.redis_client import get_redis

logger = logging.getLogger(__name__)

_TTL_SECONDS = 86400


class RedisCollectProgress(CollectProgressPort):
    """采集进度（Redis Hash）"""

    @staticmethod
    def _key(task_id: int) -> str:
        return f"collect:progress:{task_id}"

    async def init(self, task_id: int, total: int) -> None:
        redis = await get_redis()
        key = self._key(task_id)
        await redis.hset(key, mapping={
            "total": str(total), "done": "0", "success": "0", "fail": "0",
            "skip": "0", "status": "running", "current": "",
        })
        await redis.expire(key, _TTL_SECONDS)

    async def set_total(self, task_id: int, total: int) -> None:
        redis = await get_redis()
        await redis.hset(self._key(task_id), "total", str(total))

    async def step(
        self, task_id: int, label: str, *, success: bool, skipped: bool,
    ) -> None:
        redis = await get_redis()
        key = self._key(task_id)
        pipe = redis.pipeline()
        pipe.hincrby(key, "done", 1)
        if success:
            pipe.hincrby(key, "success", 1)
        else:
            pipe.hincrby(key, "fail", 1)
        if skipped:
            pipe.hincrby(key, "skip", 1)
        pipe.hset(key, "current", label)
        await pipe.execute()

    async def set_status(self, task_id: int, status: str) -> None:
        redis = await get_redis()
        await redis.hset(self._key(task_id), "status", status)


__all__ = ["RedisCollectProgress"]
