"""采集任务注册表（task_type → handler）

注意：
  与既有 infrastructure/tasks/registry.py 是两件事。
  既有 registry.py 管 asyncio.Task 生命周期（池操作 PoolOperation 用），
  本文件管 task_type → BaseCollectTask 子类实例的字典（采集管理用）。
  两者职责不同，并存。

配套设计文档：docs/dev/07collect-class/01-collect-task-class-design.md §4.1
              docs/dev/step2/02datamanage/01-采集管理四维重构方案.md
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from infrastructure.adapter.scheduler.collect.base import BaseCollectTask

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Facet 预设（5 大面 — UI 排序 + 图标）
# ═══════════════════════════════════════════════════════════════════════════════

_FACET_DEFS: list[dict] = [
    {"facet": "tech",         "label": "技术面",     "icon": "TrendCharts", "sort_order": 1},
    {"facet": "capital",      "label": "资金面",     "icon": "Money",       "sort_order": 2},
    {"facet": "fundamental",  "label": "基本面",     "icon": "PieChart",    "sort_order": 3},
    {"facet": "news",         "label": "新闻面",     "icon": "Document",    "sort_order": 4},
    {"facet": "market",       "label": "市场全局",   "icon": "Connection",  "sort_order": 5},
]
_FACET_BY_KEY: dict[str, dict] = {f["facet"]: f for f in _FACET_DEFS}


# ═══════════════════════════════════════════════════════════════════════════════
# Catalog 数据类（供 /collect/catalog 返回）
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class TaskDef:
    """采集任务元数据（catalog 接口的最小单元）"""

    task_type: str
    label: str
    description: str
    status: str  # ready / planned


@dataclass
class FacetGroup:
    """采集任务目录树（按 facet → sub_facet 二级聚合）"""

    facet: str
    label: str
    icon: str
    sort_order: int
    sub_groups: dict[str, list[TaskDef]] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# 注册表
# ═══════════════════════════════════════════════════════════════════════════════


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

    # ── Catalog 接口（PR2 新增） ────────────────────────────────────────

    def catalog(self) -> list[FacetGroup]:
        """返回按 facet → sub_facet 二级聚合的目录树

        排序：
          1) facet 按预设 sort_order 升序
          2) sub_facet 按 task_type 字符串升序（无更细粒度排序，保持稳定）
          3) 同一 sub_facet 下按 task.label 升序

        用途：前端 CollectManage 左树渲染 + 启动按钮组。
        """
        # 初始化 5 个 facet group（按预设顺序）
        groups: dict[str, FacetGroup] = {}
        for f in _FACET_DEFS:
            groups[f["facet"]] = FacetGroup(
                facet=f["facet"],
                label=f["label"],
                icon=f["icon"],
                sort_order=f["sort_order"],
            )

        # 遍历 handler 填充
        for handler in self._handlers.values():
            facet_key = handler.facet
            if facet_key not in groups:
                logger.warning(
                    "task [%s] 的 facet=%r 不在预设中（%s），跳过 catalog 输出",
                    handler.name, facet_key, list(groups.keys()),
                )
                continue

            group = groups[facet_key]
            sub_key = handler.sub_facet or "_default"

            td = TaskDef(
                task_type=handler.name,
                label=handler.label or handler.name,
                description=handler.description,
                status=handler.status or "ready",
            )

            group.sub_groups.setdefault(sub_key, []).append(td)

        # sub_facet 内排序 + 过滤空 group
        result: list[FacetGroup] = []
        for f in _FACET_DEFS:
            g = groups[f["facet"]]
            if not g.sub_groups:
                continue
            # sub_facet 内按 label 排序
            for tasks in g.sub_groups.values():
                tasks.sort(key=lambda t: t.label)
            # sub_facet 字典按 key 排序（Python 3.7+ 字典有序）
            g.sub_groups = dict(sorted(g.sub_groups.items()))
            result.append(g)

        return result


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
    "FacetGroup",
    "TaskDef",
    "setup_collect_task_registry",
    "get_collect_task_registry",
]