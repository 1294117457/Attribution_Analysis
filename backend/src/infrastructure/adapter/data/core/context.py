"""调用上下文基础设施侧：sleep_cancellable

contextvars 契约（call_policy / cancel_check）定义在 application.port.data.context
（callers 与 Gateway 之间的契约放在应用层）。
本模块 re-export 这两个符号以保持旧 import 路径向后兼容；
infra 内部代码（gateway / decorators）继续从 context.py 导入，使用体验不变。

sleep_cancellable 仍在本文件 —— 它是数据层的"实现细节"（按 1 秒步长等待+检查）。

配套设计文档：docs/backend-docs/dev/step5/03collect优化/02-端口与基础设施实现.md §4
"""
from __future__ import annotations

import asyncio

from application.port.data.context import call_policy, cancel_check


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
