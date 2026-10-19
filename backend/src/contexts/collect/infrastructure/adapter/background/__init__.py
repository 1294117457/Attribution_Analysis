"""background — collect 后台任务基础设施

参考：user.contexts.infrastructure.adapter.background.operation_dispatcher
"""
from contexts.collect.infrastructure.adapter.background.collect_task_runner import (
    CollectTaskRunner,
    get_collect_task_runner,
)

__all__ = ["CollectTaskRunner", "get_collect_task_runner"]
