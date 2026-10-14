"""采集任务占位（planned）— 未实现的少量占位"""
from __future__ import annotations

import logging

from application.collect.task import BaseCollectTask, TaskSummary

logger = logging.getLogger(__name__)


class PlannedCollectTask(BaseCollectTask):
    """占位任务：UI 列出但 run() 返回'待实现'

    子类只需声明 4 个元数据类变量（facet / sub_facet / label / description）+ name。
    """

    status = "planned"

    async def estimate_total(self, params: dict) -> int:
        return 0

    async def run(self, params: dict, on_unit_done) -> TaskSummary:
        logger.info(
            "task [%s] 尚未实现 — 等待 %s fetcher 接入",
            self.name, self.sub_facet or self.facet,
        )
        return TaskSummary(
            success=0,
            fail=1,
            total_count=0,
            message=(
                f"任务 [{self.name}] 尚未实现，请等待 fetcher 接入"
            ),
        )


class MinuteKlineCollectTask(PlannedCollectTask):
    """分钟 K 线入库（Pytdx 入库版；实时查询见 StockMinuteKlineQuery）"""

    name = "minute_kline"
    facet = "tech"
    sub_facet = "kline"
    label = "分钟 K 线"
    description = "分钟 K 入库（占位）；实时查询见实时接口 stock_minute_kline"


class NewsArticleCollectTask(PlannedCollectTask):
    """新闻资讯（tushare news 权限未开通 + ORM 未建）"""

    name = "news_article"
    facet = "news"
    sub_facet = "article"
    label = "新闻资讯"
    description = "tushare news 权限待开通（pending）"


def all_planned_tasks() -> list[BaseCollectTask]:
    """返回剩余的 planned 占位任务实例（用于 setup_collect 批量注册）"""
    return [
        MinuteKlineCollectTask(),
        NewsArticleCollectTask(),
    ]


__all__ = [
    "MinuteKlineCollectTask",
    "NewsArticleCollectTask",
    "PlannedCollectTask",
    "all_planned_tasks",
]
