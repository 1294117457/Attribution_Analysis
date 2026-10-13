"""采集任务抽象与子类 — 重导出

公开 API（供 main.py lifespan 与 route 层使用）：

子类：
  - DailyKlineCollectTask
  - DailyBasicCollectTask
  - FinReportCollectTask（tushare income · 利润表）
  - StockBasicCollectTask
  - ConceptListCollectTask / ConceptMembershipCollectTask / ConceptIndexTHCollectTask（adata · 同花顺）

抽象：
  - BaseCollectTask
  - UnitResult / TaskSummary / Cancelled

模板方法：
  - execute_task

注册表：
  - CollectTaskRegistry
  - setup_collect_task_registry

取消标志：
  - request_cancel / is_cancelled / clear_cancel

配套设计文档：docs/dev/07collect-class/01-collect-task-class-design.md
"""

from infrastructure.adapter.collect.base import (
    BaseCollectTask,
    Cancelled,
    TaskSummary,
    UnitResult,
    clear_cancel,
    execute_task,
    is_cancelled,
    request_cancel,
)
from infrastructure.adapter.collect.concept import (
    ConceptIndexTHCollectTask,
    ConceptListCollectTask,
    ConceptMembershipCollectTask,
)
from infrastructure.adapter.collect.concept_reason import ConceptReasonCollectTask
from infrastructure.adapter.collect.concept_snapshot import ConceptSnapshotCollectTask
from infrastructure.adapter.collect.daily_kline import DailyKlineCollectTask
from infrastructure.adapter.collect.declarative import DeclarativeCollectTask
from infrastructure.adapter.collect.tushare_tasks import (
    BaseAdjFactorCollectTask,
    BaseDividendCollectTask,
    BaseNameChangeCollectTask,
    BaseSuspendCollectTask,
    CapBlockTradeCollectTask,
    CapHolderNumCollectTask,
    CapMarginDetailCollectTask,
    CapMoneyflowCollectTask,
    CapTopInstCollectTask,
    CapTopListCollectTask,
    DailyBasicCollectTask,
    FinReportCollectTask,
    FinTop10FloatHoldersCollectTask,
    FinTop10HoldersCollectTask,
)
from infrastructure.adapter.collect.planned import (
    PlannedCollectTask,
    all_planned_tasks,
)
from infrastructure.adapter.collect.registry import (
    CollectTaskRegistry,
    FacetGroup,
    TaskDef,
    get_collect_task_registry,
    setup_collect_task_registry,
)
from infrastructure.adapter.collect.stock_basic import StockBasicCollectTask

__all__ = [
    # 子类
    "DailyBasicCollectTask",
    "DailyKlineCollectTask",
    "FinReportCollectTask",
    "StockBasicCollectTask",
    "ConceptListCollectTask",
    "ConceptMembershipCollectTask",
    "ConceptIndexTHCollectTask",
    "ConceptReasonCollectTask",
    "ConceptSnapshotCollectTask",
    # 资金面（13 资金面/基本面/基础层 新增）
    "CapMoneyflowCollectTask",
    "CapMarginDetailCollectTask",
    "CapTopListCollectTask",
    "CapTopInstCollectTask",
    "CapBlockTradeCollectTask",
    "CapHolderNumCollectTask",
    "FinTop10HoldersCollectTask",
    "FinTop10FloatHoldersCollectTask",
    "BaseAdjFactorCollectTask",
    "BaseSuspendCollectTask",
    "BaseNameChangeCollectTask",
    "BaseDividendCollectTask",
    # 抽象
    "BaseCollectTask",
    "DeclarativeCollectTask",
    "UnitResult",
    "TaskSummary",
    "Cancelled",
    # 模板方法
    "execute_task",
    # 注册表
    "CollectTaskRegistry",
    "FacetGroup",
    "TaskDef",
    "setup_collect_task_registry",
    "get_collect_task_registry",
    # 取消标志
    "request_cancel",
    "is_cancelled",
    "clear_cancel",
    # 占位任务（planned）
    "PlannedCollectTask",
    "all_planned_tasks",
]
