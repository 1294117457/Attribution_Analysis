"""采集任务抽象与子类 — 重导出

公开 API（供 main.py lifespan 与 route 层使用）：

子类：
  - DailyKlineCollectTask
  - DailyBasicCollectTask
  - StockBasicCollectTask
  - ConceptCollectTask

抽象：
  - BaseCollectTask
  - UnitResult / TaskSummary / Cancelled

模板方法：
  - execute_task

注册表：
  - CollectTaskRegistry
  - setup_collect_task_registry
  - get_collect_task_registry

取消标志：
  - request_cancel / is_cancelled / clear_cancel

配套设计文档：docs/dev/07collect-class/01-collect-task-class-design.md
"""

from infrastructure.tasks.collect.base import (
    BaseCollectTask,
    Cancelled,
    TaskSummary,
    UnitResult,
    clear_cancel,
    execute_task,
    is_cancelled,
    request_cancel,
)
from infrastructure.tasks.collect.concept import ConceptCollectTask
from infrastructure.tasks.collect.daily_basic import DailyBasicCollectTask
from infrastructure.tasks.collect.daily_kline import DailyKlineCollectTask
from infrastructure.tasks.collect.registry import (
    CollectTaskRegistry,
    get_collect_task_registry,
    setup_collect_task_registry,
)
from infrastructure.tasks.collect.stock_basic import StockBasicCollectTask

__all__ = [
    # 子类
    "ConceptCollectTask",
    "DailyBasicCollectTask",
    "DailyKlineCollectTask",
    "StockBasicCollectTask",
    # 抽象
    "BaseCollectTask",
    "UnitResult",
    "TaskSummary",
    "Cancelled",
    # 模板方法
    "execute_task",
    # 注册表
    "CollectTaskRegistry",
    "setup_collect_task_registry",
    "get_collect_task_registry",
    # 取消标志
    "request_cancel",
    "is_cancelled",
    "clear_cancel",
]
