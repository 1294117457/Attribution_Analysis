"""采集用例子系统（应用层）

公开 API（供 main.py lifespan 与 route 层使用）：

子类（业务任务在 application/collect/tasks/）：
  - 14 个声明式任务（tushare）
  - 日 K / 股票清单
  - 5 个概念任务
  - 2 个占位任务

抽象：
  - BaseCollectTask
  - UnitResult / TaskSummary / Cancelled
  - run_units

Runner / Context：
  - CollectRunner
  - CollectContext

注册表：
  - CollectTaskRegistry
  - setup_collect

取消标志：
  - request_cancel / is_cancelled / clear_cancel
"""
from application.collect.context import CollectContext
from application.collect.declarative import DeclarativeCollectTask
from application.collect.planners import (
    SymbolPlanner,
    TradeDatePlanner,
    UnitPlanner,
)
from application.collect.registry import (
    CollectTaskRegistry,
    FacetGroup,
    TaskDef,
    get_collect_task_registry,
    setup_collect,
)
from application.collect.runner import CollectRunner
from application.collect.task import (
    RETRY_DELAY,
    BaseCollectTask,
    Cancelled,
    TaskSummary,
    UnitResult,
    UnitTally,
    clear_cancel,
    is_cancelled,
    parse_date,
    request_cancel,
    resolve_trade_dates,
    run_units,
)


__all__ = [
    # 抽象
    "BaseCollectTask",
    "DeclarativeCollectTask",
    "UnitResult",
    "UnitTally",
    "TaskSummary",
    "Cancelled",
    "RETRY_DELAY",
    "run_units",
    "parse_date",
    "resolve_trade_dates",
    # Planner
    "SymbolPlanner",
    "TradeDatePlanner",
    "UnitPlanner",
    # Context / Runner
    "CollectContext",
    "CollectRunner",
    # 注册表
    "CollectTaskRegistry",
    "FacetGroup",
    "TaskDef",
    "setup_collect",
    "get_collect_task_registry",
    # 取消标志
    "request_cancel",
    "is_cancelled",
    "clear_cancel",
]
