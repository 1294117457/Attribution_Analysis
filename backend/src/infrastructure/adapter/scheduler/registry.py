"""异步任务注册表"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TaskRegistry:
    """全局任务注册表

    使用 dict 管理 asyncio.Task，支持取消和状态查询。
    """

    MAX_CONCURRENT = 3

    def __init__(self):
        self._tasks: dict[int, asyncio.Task] = {}

    def register(self, op_id: int, task: asyncio.Task) -> bool:
        """注册任务。如果并发超限则拒绝注册并返回 False。"""
        running_count = len(self.list_running())
        if running_count >= self.MAX_CONCURRENT:
            logger.warning("并发任务数已达上限: %d", self.MAX_CONCURRENT)
            return False
        self._tasks[op_id] = task
        logger.info("任务注册: op_id=%d", op_id)
        return True

    def unregister(self, op_id: int) -> None:
        self._tasks.pop(op_id, None)
        logger.info("任务注销: op_id=%d", op_id)

    def get(self, op_id: int) -> Optional[asyncio.Task]:
        return self._tasks.get(op_id)

    def cancel(self, op_id: int) -> bool:
        task = self._tasks.get(op_id)
        if task and not task.done():
            task.cancel()
            logger.info("任务已取消: op_id=%d", op_id)
            return True
        return False

    def is_running(self, op_id: int) -> bool:
        task = self._tasks.get(op_id)
        return task is not None and not task.done()

    def list_running(self) -> list[int]:
        return [op_id for op_id, task in self._tasks.items() if not task.done()]

    @property
    def count(self) -> int:
        return len(self._tasks)


_global_registry: Optional[TaskRegistry] = None


def get_task_registry() -> TaskRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = TaskRegistry()
    return _global_registry
