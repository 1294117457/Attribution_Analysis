"""采集任务占位（planned）— 资金面 / 基础层 / 基本面深度 / 新闻面

设计：
- 这些 task 暂未实现 fetcher，但已在 catalog 中暴露，让用户看见完整蓝图
- UI 标灰 + 「待实现」标签，避免误点
- run() 直接返回"待实现"提示，不调用任何远程 API

替代关系：当某个 task 真正接入 fetcher 时，新建子类继承 BaseCollectTask，
        把对应的 Planned 子类从 lifespan 注册列表中移除即可。

配套设计文档：
  docs/dev/step2/02datamanage/01-采集管理四维重构方案.md §2.5
  docs/dev/step1/03dataana/01data.md  §1.3 (14 张新增表清单)
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
# 技术面 — 基础层（复权 / 停复牌 / 曾用名）
# ═══════════════════════════════════════════════════════════════════════════════


class BaseAdjFactorCollectTask(PlannedCollectTask):
    """复权因子采集"""

    name = "base_adj_factor"
    facet = "tech"
    sub_facet = "base"
    label = "复权因子"
    description = "计算前/后复权价格（tushare adj_factor，~125万行/年）"


class BaseSuspendCollectTask(PlannedCollectTask):
    """停复牌事件"""

    name = "base_suspend"
    facet = "tech"
    sub_facet = "base"
    label = "停复牌"
    description = "标识 K 线断点（tushare suspend_d）"


class BaseNameChangeCollectTask(PlannedCollectTask):
    """股票曾用名"""

    name = "base_name_change"
    facet = "tech"
    sub_facet = "base"
    label = "股票曾用名"
    description = "历史 K 线展示 / ST 等改名场景（tushare namechange）"


class MinuteKlineCollectTask(PlannedCollectTask):
    """分钟 K 线（Pytdx 实时拉取）"""

    name = "minute_kline"
    facet = "tech"
    sub_facet = "kline"
    label = "分钟 K 线"
    description = "Pytdx 通达信 1/5/15/30/60min（实时拉取，不入库）"


# ═══════════════════════════════════════════════════════════════════════════════
# 资金面（6 张表 + 1 基础实体 — 1 实体仅 ORM，列 planned 用于覆盖）
# ═══════════════════════════════════════════════════════════════════════════════


class CapMarginDetailCollectTask(PlannedCollectTask):
    """个股融资融券明细"""

    name = "cap_margin_detail"
    facet = "capital"
    sub_facet = "margin"
    label = "个股融资融券"
    description = "3000+ 只两融标的（tushare margin_detail）"


class CapMoneyflowCollectTask(PlannedCollectTask):
    """个股资金流向"""

    name = "cap_moneyflow"
    facet = "capital"
    sub_facet = "moneyflow"
    label = "个股资金流向"
    description = "大/中/小单买卖与净流入（tushare moneyflow，~125万行/年）"


class CapTopListCollectTask(PlannedCollectTask):
    """龙虎榜每日上榜"""

    name = "cap_top_list"
    facet = "capital"
    sub_facet = "dragon_tiger"
    label = "龙虎榜每日"
    description = "龙虎榜上榜汇总（tushare top_list）"


class CapTopInstCollectTask(PlannedCollectTask):
    """龙虎榜机构席位"""

    name = "cap_top_inst"
    facet = "capital"
    sub_facet = "dragon_tiger"
    label = "龙虎榜机构"
    description = "机构专用席位明细（tushare top_inst）"


class CapBlockTradeCollectTask(PlannedCollectTask):
    """大宗交易"""

    name = "cap_block_trade"
    facet = "capital"
    sub_facet = "block_trade"
    label = "大宗交易"
    description = "折溢价 + 买卖方识别（tushare block_trade）"


class CapHolderNumCollectTask(PlannedCollectTask):
    """股东户数"""

    name = "cap_holder_num"
    facet = "capital"
    sub_facet = "chip"
    label = "股东户数"
    description = "筹码集中度（tushare stk_holdernumber，季频）"


# ═══════════════════════════════════════════════════════════════════════════════
# 基本面（季报 / 十大股东 / 分红送股）
# ═══════════════════════════════════════════════════════════════════════════════


class FinReportCollectTask(PlannedCollectTask):
    """季报财务指标"""

    name = "fin_report"
    facet = "fundamental"
    sub_facet = "report"
    label = "季报财务"
    description = "盈利 / 成长 / 偿债 / 现金流（tushare fina_indicator）"


class FinTop10HoldersCollectTask(PlannedCollectTask):
    """前十大股东"""

    name = "fin_top10_holders"
    facet = "fundamental"
    sub_facet = "holder"
    label = "前十大股东"
    description = "股权结构（tushare top10_holders，季频）"


class FinTop10FloatHoldersCollectTask(PlannedCollectTask):
    """前十大流通股东"""

    name = "fin_top10_floatholders"
    facet = "fundamental"
    sub_facet = "holder"
    label = "前十大流通股东"
    description = "流通盘筹码（tushare top10_floatholders）"


class BaseDividendCollectTask(PlannedCollectTask):
    """分红送股"""

    name = "base_dividend"
    facet = "fundamental"
    sub_facet = "dividend"
    label = "分红送股"
    description = "复权事件 + 高股息筛选（tushare dividend）"


# ═══════════════════════════════════════════════════════════════════════════════
# 新闻面（pending — 等 tushare news 权限）
# ═══════════════════════════════════════════════════════════════════════════════


class NewsArticleCollectTask(PlannedCollectTask):
    """新闻资讯"""

    name = "news_article"
    facet = "news"
    sub_facet = "article"
    label = "新闻资讯"
    description = "tushare news 权限待开通（pending）"


# ═══════════════════════════════════════════════════════════════════════════════
# 一次性注册 helper（main.py lifespan 调用）
# ═══════════════════════════════════════════════════════════════════════════════


def all_planned_tasks() -> list[BaseCollectTask]:
    """返回所有 planned 任务实例（用于 lifespan 批量注册）"""
    return [
        # 技术面 — 基础层
        BaseAdjFactorCollectTask(),
        BaseSuspendCollectTask(),
        BaseNameChangeCollectTask(),
        MinuteKlineCollectTask(),
        # 资金面
        CapMarginDetailCollectTask(),
        CapMoneyflowCollectTask(),
        CapTopListCollectTask(),
        CapTopInstCollectTask(),
        CapBlockTradeCollectTask(),
        CapHolderNumCollectTask(),
        # 基本面
        FinReportCollectTask(),
        FinTop10HoldersCollectTask(),
        FinTop10FloatHoldersCollectTask(),
        BaseDividendCollectTask(),
        # 新闻面
        NewsArticleCollectTask(),
    ]


__all__ = [
    "PlannedCollectTask",
    # tech / base
    "BaseAdjFactorCollectTask",
    "BaseSuspendCollectTask",
    "BaseNameChangeCollectTask",
    "MinuteKlineCollectTask",
    # capital
    "CapMarginDetailCollectTask",
    "CapMoneyflowCollectTask",
    "CapTopListCollectTask",
    "CapTopInstCollectTask",
    "CapBlockTradeCollectTask",
    "CapHolderNumCollectTask",
    # fundamental
    "FinReportCollectTask",
    "FinTop10HoldersCollectTask",
    "FinTop10FloatHoldersCollectTask",
    "BaseDividendCollectTask",
    # news
    "NewsArticleCollectTask",
    "all_planned_tasks",
]