"""实时查询框架 port

DDD.md §2.2 / §4：application 定义 port，由 infrastructure 实现。
实现位于 `infrastructure.adapter.realtime.framework.RealtimeQueryFramework`。
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class RealtimeResultLike(Protocol):
    """实时查询结果（最小化结构子集）"""

    data: Any
    cached: bool
    stale: bool
    fetched_at: Any
    latency_ms: int
    error: Any


class RealtimeQueryPort(Protocol):
    """实时接口查询 port

    - query(name, params) -> RealtimeResultLike
    - query_many(name, params_list) -> list[RealtimeResultLike]
    """

    def query(self, name: str, params: dict) -> Any: ...

    def query_many(self, name: str, params_list: list[dict]) -> list[Any]: ...