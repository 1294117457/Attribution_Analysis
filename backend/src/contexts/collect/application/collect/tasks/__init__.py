"""采集任务总入口 — 供 main.py lifespan 与 route 层使用"""
from contexts.collect.application.collect.task import BaseCollectTask
from contexts.collect.application.collect.tasks.concept import (
    ConceptIndexTHCollectTask,
    ConceptListCollectTask,
    ConceptMembershipCollectTask,
)
from contexts.collect.application.collect.tasks.concept_reason import ConceptReasonCollectTask
from contexts.collect.application.collect.tasks.concept_snapshot import ConceptSnapshotCollectTask
from contexts.collect.application.collect.tasks.daily_kline import DailyKlineCollectTask
from contexts.collect.application.collect.tasks.planned import (
    MinuteKlineCollectTask,
    NewsArticleCollectTask,
    PlannedCollectTask,
    all_planned_tasks,
)
from contexts.collect.application.collect.tasks.stock_basic import StockBasicCollectTask
from contexts.collect.application.collect.tasks.tushare import (
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


def all_collect_tasks() -> list[BaseCollectTask]:
    """返回全部 23 个采集任务实例（用于 setup_collect 批量注册）"""
    return [
        # 已实现的基础任务
        StockBasicCollectTask(),
        DailyKlineCollectTask(),
        # 14 个声明式
        DailyBasicCollectTask(),
        BaseSuspendCollectTask(),
        CapMoneyflowCollectTask(),
        CapMarginDetailCollectTask(),
        CapTopListCollectTask(),
        CapTopInstCollectTask(),
        CapBlockTradeCollectTask(),
        BaseAdjFactorCollectTask(),
        BaseDividendCollectTask(),
        CapHolderNumCollectTask(),
        FinTop10HoldersCollectTask(),
        FinTop10FloatHoldersCollectTask(),
        FinReportCollectTask(),
        BaseNameChangeCollectTask(),
        # 5 个概念
        ConceptListCollectTask(),
        ConceptMembershipCollectTask(),
        ConceptIndexTHCollectTask(),
        ConceptReasonCollectTask(),
        ConceptSnapshotCollectTask(),
        # 2 个占位
        *all_planned_tasks(),
    ]


__all__ = [
    "all_collect_tasks",
    "all_planned_tasks",
    # 23 个任务类
    "DailyKlineCollectTask",
    "DailyBasicCollectTask",
    "FinReportCollectTask",
    "StockBasicCollectTask",
    "ConceptListCollectTask",
    "ConceptMembershipCollectTask",
    "ConceptIndexTHCollectTask",
    "ConceptReasonCollectTask",
    "ConceptSnapshotCollectTask",
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
    "MinuteKlineCollectTask",
    "NewsArticleCollectTask",
    "PlannedCollectTask",
]
