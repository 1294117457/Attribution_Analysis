"""池操作派发器 port

DDD.md §2.2 / §4：application 定义 port 接口，由 infrastructure 实现。
实现位于 `infrastructure.adapter.scheduler.operation_dispatcher.OperationDispatcher`。
"""
from __future__ import annotations

from typing import Protocol


class OperationDispatcherPort(Protocol):
    """后台任务派发与取消

    - dispatch_kline_collect: 派发一个 K 线采集任务（内部开 session，不阻塞父请求）
    - cancel_operation: 取消一个运行中任务
    """

    async def dispatch_kline_collect(
        self,
        *,
        op_id: int,
        pool_id: int,
        symbols: list[str],
        days: int = 365,
    ) -> None: ...

    async def cancel_operation(self, op_id: int) -> bool: ...