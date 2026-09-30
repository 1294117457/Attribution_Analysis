"""实时接口注册表（name → BaseRealtimeQuery 实例），由 main.py lifespan 初始化"""

from __future__ import annotations

import logging
from typing import Optional

from infrastructure.adapter.realtime.base import BaseRealtimeQuery

logger = logging.getLogger(__name__)


class RealtimeQueryRegistry:
    def __init__(self) -> None:
        self._queries: dict[str, BaseRealtimeQuery] = {}

    def register(self, query: BaseRealtimeQuery) -> None:
        if not query.name:
            raise ValueError(f"{type(query).__name__} 未设置 name")
        if query.name in self._queries:
            raise ValueError(f"实时接口 {query.name} 已注册")
        self._queries[query.name] = query
        logger.info("注册实时接口: %s → %s", query.name, type(query).__name__)

    def get(self, name: str) -> Optional[BaseRealtimeQuery]:
        return self._queries.get(name)

    def all(self) -> list[BaseRealtimeQuery]:
        return list(self._queries.values())


_registry: Optional[RealtimeQueryRegistry] = None


def setup_realtime_registry(queries: list[BaseRealtimeQuery]) -> RealtimeQueryRegistry:
    global _registry
    _registry = RealtimeQueryRegistry()
    for q in queries:
        _registry.register(q)
    return _registry


def get_realtime_registry() -> RealtimeQueryRegistry:
    """未初始化时返回空注册表（单测 / 脚本场景）"""
    global _registry
    if _registry is None:
        _registry = RealtimeQueryRegistry()
    return _registry
