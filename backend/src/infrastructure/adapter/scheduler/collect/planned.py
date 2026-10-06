"""采集任务占位（planned）— 未实现的少量占位

⚠️ 2026-10-04 重大变更：原本这里定义了 13 个 planned 占位类（资金面 6 + 基本面深度 3 + 基础层 3 + 分钟 K 入库版 + news_article）。
   这些中 13 个已被真正实现（参见 collect/{cap_*, fin_top10_*, base_*, concept_*} 子模块），
   已**从本文件删除**（避免与同名已实现类混淆）。

保留：2 个真正还未实现的占位类（minute_kline 入库版 + news_article）

配套设计文档：
  docs/dev/step2/02datamanage/01-采集管理四维重构方案.md §2.5
"""

from __future__ import annotations

import logging

from infrastructure.adapter.scheduler.collect.base import (
    BaseCollectTask,
    TaskSummary,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 抽象基类
# ═══════════════════════════════════════════════════════════════════════════════


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
                f"任务 [{self.name}] 尚未实现，"
                f"请等待 fetcher 接入"
            ),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 仅保留 2 个真正未实现的占位类
# ═══════════════════════════════════════════════════════════════════════════════


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


# ═══════════════════════════════════════════════════════════════════════════════
# 一次性注册 helper（main.py lifespan 调用）
# ═══════════════════════════════════════════════════════════════════════════════


def all_planned_tasks() -> list[BaseCollectTask]:
    """返回剩余的 planned 占位任务实例（用于 lifespan 批量注册）

    2026-10-04 大规模实现后，已实现 13 个 task 被移出本函数：
    - 技术面：base_adj_factor / base_suspend / base_name_change
    - 资金面：cap_margin_detail / cap_moneyflow / cap_top_list / cap_top_inst / cap_block_trade / cap_holder_num
    - 基本面：fin_top10_holders / fin_top10_floatholders / base_dividend / concept_reason / concept_snapshot

    剩余 planned：仅 minute_kline（入库版）和 news_article（权限未开通 + ORM 未建）。
    """
    return [
        # 技术面 — 分钟 K 入库版（实时查询已可用，单独入口见 StockMinuteKlineQuery）
        MinuteKlineCollectTask(),
        # 新闻面（tushare news 权限未开通 + ORM 未建）
        NewsArticleCollectTask(),
    ]


__all__ = [
    "PlannedCollectTask",
    # 仅 2 个真正未实现
    "MinuteKlineCollectTask",
    "NewsArticleCollectTask",
    "all_planned_tasks",
]