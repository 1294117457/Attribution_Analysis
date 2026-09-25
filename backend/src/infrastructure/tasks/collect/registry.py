"""采集任务注册表（task_type → handler）

注意：
  与既有 infrastructure/tasks/registry.py 是两件事。
  既有 registry.py 管 asyncio.Task 生命周期（池操作 PoolOperation 用），
  本文件管 task_type → BaseCollectTask 子类实例的字典（采集管理用）。
  两者职责不同，并存。

配套设计文档：docs/dev/07collect-class/01-collect-task-class-design.md §4.1
"""

from __future__ import annotations

import logging

from infrastructure.tasks.collect.base import BaseCollectTask

logger = logging.getLogger(__name__)


class CollectTaskRegistry:
    """task_type → BaseCollectTask 实例 的字典注册表

    设计决策：使用 dict 实例而非工厂函数
      · 4 个 task_type 全部无状态或 fetcher 池已做隔离
      · dict 查找比工厂调用快 ~100x，hot path 友好
      · 子类可在 pre_execute() 内自行建池，无需框架操心
    """

    def __init__(self) -> None:
        self._handlers: dict[str, BaseCollectTask] = {}

    def register(self, task_type: str, handler: BaseCollectTask) -> None:
        """注册一个 task_type → handler 映射"""
        if task_type in self._handlers:
            raise ValueError(f"task_type {task_type} 已注册")
        if not handler.name:
            raise ValueError(
                f"handler {type(handler).__name__} 未设置 name 类变量"
            )
        if handler.name != task_type:
            raise ValueError(
                f"handler.name={handler.name} 与 task_type={task_type} 不一致"
            )
        self._handlers[task_type] = handler
        logger.info("注册采集任务: %s → %s", task_type, type(handler).__name__)

    def get(self, task_type: str) -> BaseCollectTask | None:
        """按 task_type 获取 handler；未注册则返回 None"""
        return self._handlers.get(task_type)

    def supported_types(self) -> list[str]:
        """已注册的 task_type 列表（用于 router 错误提示）"""
        return list(self._handlers.keys())


# ═══════════════════════════════════════════════════════════════════════════════
# 全局注册表（模块单例，由 lifespan 启动期初始化）
# ═══════════════════════════════════════════════════════════════════════════════

_collect_registry: CollectTaskRegistry | None = None


def setup_collect_task_registry(handlers: list[BaseCollectTask]) -> CollectTaskRegistry:
    """应用启动时调用一次：注入所有 handler 并完成注册

    在 main.py 的 lifespan 中调用。
    """
    global _collect_registry
    _collect_registry = CollectTaskRegistry()
    for h in handlers:
        _collect_registry.register(h.name, h)
    return _collect_registry


def get_collect_task_registry() -> CollectTaskRegistry:
    """获取全局注册表

    Raises:
        RuntimeError: 注册表未初始化（未调用 setup_collect_task_registry）
    """
    global _collect_registry
    if _collect_registry is None:
        raise RuntimeError(
            "采集任务注册表未初始化，请先调用 setup_collect_task_registry"
        )
    return _collect_registry


__all__ = [
    "CollectTaskRegistry",
    "setup_collect_task_registry",
    "get_collect_task_registry",
]
