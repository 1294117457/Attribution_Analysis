"""采集任务注册表（task_type → handler）

实时接口目录由 ctx.gateway 提供。
全局单例由 di 持有。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from application.collect.context import CollectContext
from application.collect.task import BaseCollectTask
from application.port.data.base import PortInfo

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Facet 预设（5 大面 — UI 排序 + 图标；与旧实现保持一致）
# ═══════════════════════════════════════════════════════════════════════════════

_FACET_DEFS: list[dict] = [
    {"facet": "tech",         "label": "技术面",     "icon": "TrendCharts", "sort_order": 1},
    {"facet": "capital",      "label": "资金面",     "icon": "Money",       "sort_order": 2},
    {"facet": "fundamental",  "label": "基本面",     "icon": "PieChart",    "sort_order": 3},
    {"facet": "news",         "label": "新闻面",     "icon": "Document",    "sort_order": 4},
    {"facet": "market",       "label": "行情",       "icon": "DataLine",    "sort_order": 5},
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
    default_params: dict = field(default_factory=dict)
    supports_run_one: bool = False
    kind: str = "batch"  # batch：采集入库；realtime：按需查询 + 缓存
    source: Optional[str] = None
    source_label: Optional[str] = None
    ttl_trading: Optional[int] = None
    consumers: tuple[str, ...] = ()


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

    setup_collect 时由 di 构造一次；handler 已绑定 ctx。
    """

    def __init__(self, ctx: CollectContext) -> None:
        self._ctx = ctx
        self._handlers: dict[str, BaseCollectTask] = {}

    def register(self, handler: BaseCollectTask) -> None:
        """注册一个 handler

        启动期校验：name / facet（不变）→ handler.bind(ctx) →
        声明式任务额外校验 raw_store.supports(port)
        """
        task_type = handler.name
        if task_type in self._handlers:
            raise ValueError(f"task_type {task_type} 已注册")
        if not handler.name:
            raise ValueError(f"handler {type(handler).__name__} 未设置 name 类变量")
        if handler.facet and handler.facet not in _FACET_BY_KEY:
            valid = list(_FACET_BY_KEY.keys())
            raise ValueError(
                f"{type(handler).__name__}.facet={handler.facet!r} 不在预设中，"
                f"请改成 {valid} 之一"
            )
        handler.bind(self._ctx)
        # 声明式任务额外校验 raw_store.supports(port)
        port = getattr(handler, "port", None)
        if port is not None:
            if not self._ctx.raw_store.supports(port):
                raise ValueError(
                    f"{type(handler).__name__}.port={port.name!r} 没有 RawDataStore 映射"
                )
        self._handlers[task_type] = handler
        logger.info("注册采集任务: %s → %s", task_type, type(handler).__name__)

    def get(self, task_type: str) -> BaseCollectTask | None:
        return self._handlers.get(task_type)

    def supported_types(self) -> list[str]:
        return list(self._handlers.keys())

    def realtime_ports(self) -> list[PortInfo]:
        return [p for p in self._ctx.gateway.catalog() if p.realtime]

    def catalog(self) -> list[FacetGroup]:
        """返回按 facet → sub_facet 二级聚合的目录树"""
        groups: dict[str, FacetGroup] = {}
        for f in _FACET_DEFS:
            groups[f["facet"]] = FacetGroup(
                facet=f["facet"],
                label=f["label"],
                icon=f["icon"],
                sort_order=f["sort_order"],
            )

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
                default_params=dict(handler.default_params),
                supports_run_one=handler.supports_collect_one,
            )
            group.sub_groups.setdefault(sub_key, []).append(td)

        realtime = self.realtime_ports()
        for q in realtime:
            group = groups.get(q.facet)
            if group is None:
                logger.warning("实时接口 [%s] 的 facet=%r 不在预设中，跳过 catalog 输出", q.name, q.facet)
                continue
            first = q.adapters[0] if q.adapters else None
            group.sub_groups.setdefault(q.sub_facet or "_default", []).append(TaskDef(
                task_type=q.name,
                label=q.label or q.name,
                description=q.description,
                status="ready",
                default_params=dict(q.sample_params),
                kind="realtime",
                source=first.origin if first else None,
                source_label=first.origin_label if first else None,
                ttl_trading=q.ttl_trading,
                consumers=tuple(q.consumers),
            ))

        order = {h.name: h.sort_order for h in self._handlers.values()}
        order.update({q.name: q.sort_order for q in realtime})
        result: list[FacetGroup] = []
        for f in _FACET_DEFS:
            g = groups[f["facet"]]
            if not g.sub_groups:
                continue
            for tasks in g.sub_groups.values():
                tasks.sort(key=lambda t: (order.get(t.task_type, 0), t.label))
            g.sub_groups = dict(sorted(g.sub_groups.items()))
            result.append(g)
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# 全局注册表（由 di 持有，lifespan 启动期初始化）
# ═══════════════════════════════════════════════════════════════════════════════

_collect_registry: Optional[CollectTaskRegistry] = None


def setup_collect(
    ctx: CollectContext,
    handlers: list[BaseCollectTask],
) -> CollectTaskRegistry:
    """应用启动时调用一次：注入 ctx 并完成注册"""
    global _collect_registry
    _collect_registry = CollectTaskRegistry(ctx)
    for h in handlers:
        _collect_registry.register(h)
    return _collect_registry


def get_collect_task_registry() -> CollectTaskRegistry:
    """获取全局注册表"""
    global _collect_registry
    if _collect_registry is None:
        raise RuntimeError(
            "采集任务注册表未初始化，请先调用 setup_collect"
        )
    return _collect_registry


__all__ = [
    "CollectTaskRegistry",
    "FacetGroup",
    "TaskDef",
    "get_collect_task_registry",
    "setup_collect",
]
