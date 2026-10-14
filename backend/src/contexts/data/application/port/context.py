"""调用上下文（contextvars 传递）：调用策略 + 取消检查

这些是"调用方 ↔ Gateway"之间的协议，应放在端口层。底层 Adapter 不感知 collect 模块；
取消标志是模块级 set，参考 application.collect.task。

配套设计文档：docs/backend-docs/dev/step5/03collect优化/02-端口与基础设施实现.md §4
"""
from __future__ import annotations

from contextvars import ContextVar
from typing import Callable, Optional

from contexts.data.application.port.base import CallPolicy

call_policy: ContextVar[CallPolicy] = ContextVar("call_policy", default=CallPolicy.COLLECT)
# 由 application.collect.CollectRunner 设置；已取消时调用即抛出 Cancelled
cancel_check: ContextVar[Optional[Callable[[], None]]] = ContextVar("cancel_check", default=None)


__all__ = ["call_policy", "cancel_check"]
