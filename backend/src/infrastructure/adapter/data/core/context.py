"""调用上下文：调用策略 / 取消检查（contextvars 传递，Adapter 签名不变）"""
from __future__ import annotations

import asyncio
from contextvars import ContextVar
from typing import Callable, Optional

from application.port.data.base import CallPolicy

call_policy: ContextVar[CallPolicy] = ContextVar("call_policy", default=CallPolicy.COLLECT)
# 由 execute_task 设置；已取消时调用即抛出（采集模块的 Cancelled），数据层不 import 采集模块
cancel_check: ContextVar[Optional[Callable[[], None]]] = ContextVar("cancel_check", default=None)


async def sleep_cancellable(seconds: float) -> None:
    """按 1 秒步长等待，每步检查取消"""
    check = cancel_check.get()
    while seconds > 0:
        if check:
            check()
        step = min(1.0, seconds)
        await asyncio.sleep(step)
        seconds -= step


__all__ = ["call_policy", "cancel_check", "sleep_cancellable"]
