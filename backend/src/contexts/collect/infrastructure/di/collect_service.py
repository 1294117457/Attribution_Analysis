"""collect context — 业务 DI 工厂

为 collect 下 28 个 service 提供 `get_xxx_service()` 工厂，按 facet 5 个目录分组。

所有 service 内部已使用 `connect/` 模块级单例 client；
fetcher 自身不依赖外部 client 注入，所以 service 可以 DefaultConstruct（无外部依赖），
DI 工厂仅按需返回新实例（无状态、线程安全）。
"""
from __future__ import annotations


# ═══════════════════════════════════════════════════════════════════════
# tech 5
# ═══════════════════════════════════════════════════════════════════════
def get_daily_kline_service():
    from contexts.collect.application.service.tech.daily_kline_service import (
        DailyKlineService,
    )
    return DailyKlineService()


def get_minute_kline_service():
    from contexts.collect.application.service.tech.minute_kline_service import (
        MinuteKlineService,
    )
    return MinuteKlineService()


def get_adj_factor_service():
    from contexts.collect.application.service.tech.adj_factor_service import (
        AdjFactorService,
    )
    return AdjFactorService()


def get_suspend_service():
    from contexts.collect.application.service.tech.suspend_service import (
        SuspendService,
    )
    return SuspendService()


def get_name_change_service():
    from contexts.collect.application.service.tech.name_change_service import (
        NameChangeService,
    )
    return NameChangeService()


# ═══════════════════════════════════════════════════════════════════════
# capital 9
# ═══════════════════════════════════════════════════════════════════════
def get_moneyflow_service():
    from contexts.collect.application.service.capital.moneyflow_service import (
        MoneyflowService,
    )
    return MoneyflowService()


def get_moneyflow_hsgt_service():
    from contexts.collect.application.service.capital.moneyflow_hsgt_service import (
        MoneyflowHsgtService,
    )
    return MoneyflowHsgtService()


def get_top_list_service():
    from contexts.collect.application.service.capital.top_list_service import (
        TopListService,
    )
    return TopListService()


def get_top_inst_service():
    from contexts.collect.application.service.capital.top_inst_service import (
        TopInstService,
    )
    return TopInstService()


def get_block_trade_service():
    from contexts.collect.application.service.capital.block_trade_service import (
        BlockTradeService,
    )
    return BlockTradeService()


def get_margin_service():
    from contexts.collect.application.service.capital.margin_service import (
        MarginService,
    )
    return MarginService()


def get_hsgt_top10_service():
    from contexts.collect.application.service.capital.hsgt_top10_service import (
        HsgtTop10Service,
    )
    return HsgtTop10Service()


def get_limit_list_service():
    from contexts.collect.application.service.capital.limit_list_service import (
        LimitListService,
    )
    return LimitListService()


def get_holder_number_service():
    from contexts.collect.application.service.capital.holder_number_service import (
        HolderNumberService,
    )
    return HolderNumberService()


# ═══════════════════════════════════════════════════════════════════════
# fundamental 12
# ═══════════════════════════════════════════════════════════════════════
def get_daily_basic_service():
    from contexts.collect.application.service.fundamental.daily_basic_service import (
        DailyBasicService,
    )
    return DailyBasicService()


def get_fin_income_service():
    from contexts.collect.application.service.fundamental.fin_income_service import (
        FinIncomeService,
    )
    return FinIncomeService()


def get_top10_holders_service():
    from contexts.collect.application.service.fundamental.top10_holders_service import (
        Top10HoldersService,
    )
    return Top10HoldersService()


def get_top10_float_holders_service():
    from contexts.collect.application.service.fundamental.top10_floatholders_service import (
        Top10FloatHoldersService,
    )
    return Top10FloatHoldersService()


def get_dividend_service():
    from contexts.collect.application.service.fundamental.dividend_service import (
        DividendService,
    )
    return DividendService()


def get_stock_basic_service():
    from contexts.collect.application.service.fundamental.stock_basic_service import (
        StockBasicService,
    )
    return StockBasicService()


def get_stock_concepts_service():
    from contexts.collect.application.service.fundamental.stock_concepts_service import (
        StockConceptsService,
    )
    return StockConceptsService()


def get_concept_list_service():
    from contexts.collect.application.service.fundamental.concept_list_service import (
        ConceptListService,
    )
    return ConceptListService()


def get_concept_members_service():
    from contexts.collect.application.service.fundamental.concept_members_service import (
        ConceptMembersService,
    )
    return ConceptMembersService()


def get_concept_index_daily_service():
    from contexts.collect.application.service.fundamental.concept_index_daily_service import (
        ConceptIndexDailyService,
    )
    return ConceptIndexDailyService()


def get_concept_minute_service():
    from contexts.collect.application.service.fundamental.concept_minute_service import (
        ConceptMinuteService,
    )
    return ConceptMinuteService()


def get_concept_snapshot_service():
    from contexts.collect.application.service.fundamental.concept_snapshot_service import (
        ConceptSnapshotService,
    )
    return ConceptSnapshotService()


# ═══════════════════════════════════════════════════════════════════════
# news 1
# ═══════════════════════════════════════════════════════════════════════
def get_news_service():
    from contexts.collect.application.service.news.news_service import (
        NewsService,
    )
    return NewsService()


# ═══════════════════════════════════════════════════════════════════════
# sentiment 1
# ═══════════════════════════════════════════════════════════════════════
def get_sentiment_service():
    from contexts.collect.application.service.sentiment.sentiment_service import (
        SentimentService,
    )
    return SentimentService()


__all__ = [
    # tech 5
    "get_daily_kline_service",
    "get_minute_kline_service",
    "get_adj_factor_service",
    "get_suspend_service",
    "get_name_change_service",
    # capital 9
    "get_moneyflow_service",
    "get_moneyflow_hsgt_service",
    "get_top_list_service",
    "get_top_inst_service",
    "get_block_trade_service",
    "get_margin_service",
    "get_hsgt_top10_service",
    "get_limit_list_service",
    "get_holder_number_service",
    # fundamental 12
    "get_daily_basic_service",
    "get_fin_income_service",
    "get_top10_holders_service",
    "get_top10_float_holders_service",
    "get_dividend_service",
    "get_stock_basic_service",
    "get_stock_concepts_service",
    "get_concept_list_service",
    "get_concept_members_service",
    "get_concept_index_daily_service",
    "get_concept_minute_service",
    "get_concept_snapshot_service",
    # news 1
    "get_news_service",
    # sentiment 1
    "get_sentiment_service",
]
