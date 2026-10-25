"""collect context — repo DI 工厂

为 25 个 repo 提供 `get_xxx_repository()` 工厂。

按 tech / capital / fundamental / concept / news 5 个分组。

service 工厂（collect_service.py）通过 Depends(get_xxx_repository) 注入。
"""
from __future__ import annotations


# ═══════════════════════════════════════════════════════════════════════
# tech (4 新增 + 2 既有)
# ═══════════════════════════════════════════════════════════════════════
def get_kline_repository():
    from contexts.collect.infrastructure.persistence.repositories.kline_repo import (
        KlineRepository,
    )
    return KlineRepository()


def get_daily_kline_repository():
    """日 K 线采集仓储（tech_daily upsert + 查询；session 由调用方传）"""
    from contexts.collect.infrastructure.persistence.repositories.tech import (
        DailyKlineRepository,
    )
    return DailyKlineRepository()


def get_trade_calendar_repository():
    """交易日历仓储（tech_trade_cal 读取；session 由调用方传）"""
    from contexts.collect.infrastructure.persistence.repositories.tech import (
        TradeCalendarRepository,
    )
    return TradeCalendarRepository()


def get_stock_name_repository():
    """股票名称映射仓储（stock_basic 读取；session 由调用方传）"""
    from contexts.collect.infrastructure.persistence.repositories.tech import (
        StockNameRepository,
    )
    return StockNameRepository()


def get_stock_info_repository():
    from contexts.collect.infrastructure.persistence.repositories.stock_info_repo import (
        StockInfoRepository,
    )
    return StockInfoRepository()


def get_adj_factor_repository():
    from contexts.collect.infrastructure.persistence.repositories.adj_factor_repo import (
        AdjFactorRepository,
    )
    return AdjFactorRepository()


def get_suspend_repository():
    from contexts.collect.infrastructure.persistence.repositories.suspend_repo import (
        SuspendRepository,
    )
    return SuspendRepository()


def get_name_change_repository():
    from contexts.collect.infrastructure.persistence.repositories.name_change_repo import (
        NameChangeRepository,
    )
    return NameChangeRepository()


def get_dividend_repository():
    from contexts.collect.infrastructure.persistence.repositories.dividend_repo import (
        DividendRepository,
    )
    return DividendRepository()


# ═══════════════════════════════════════════════════════════════════════
# capital 9
# ═══════════════════════════════════════════════════════════════════════
def get_moneyflow_repository():
    from contexts.collect.infrastructure.persistence.repositories.moneyflow_repo import (
        MoneyflowRepository,
    )
    return MoneyflowRepository()


def get_moneyflow_hsgt_repository():
    from contexts.collect.infrastructure.persistence.repositories.moneyflow_hsgt_repo import (
        MoneyflowHsgtRepository,
    )
    return MoneyflowHsgtRepository()


def get_top_list_repository():
    from contexts.collect.infrastructure.persistence.repositories.top_list_repo import (
        TopListRepository,
    )
    return TopListRepository()


def get_top_inst_repository():
    from contexts.collect.infrastructure.persistence.repositories.top_inst_repo import (
        TopInstRepository,
    )
    return TopInstRepository()


def get_block_trade_repository():
    from contexts.collect.infrastructure.persistence.repositories.block_trade_repo import (
        BlockTradeRepository,
    )
    return BlockTradeRepository()


def get_margin_detail_repository():
    from contexts.collect.infrastructure.persistence.repositories.margin_detail_repo import (
        MarginDetailRepository,
    )
    return MarginDetailRepository()


def get_hsgt_top10_repository():
    from contexts.collect.infrastructure.persistence.repositories.hsgt_top10_repo import (
        HsgtTop10Repository,
    )
    return HsgtTop10Repository()


def get_limit_list_repository():
    from contexts.collect.infrastructure.persistence.repositories.limit_list_repo import (
        LimitListRepository,
    )
    return LimitListRepository()


def get_holder_number_repository():
    from contexts.collect.infrastructure.persistence.repositories.holder_number_repo import (
        HolderNumberRepository,
    )
    return HolderNumberRepository()


# ═══════════════════════════════════════════════════════════════════════
# fundamental 5
# ═══════════════════════════════════════════════════════════════════════
def get_fin_daily_basic_repository():
    from contexts.collect.infrastructure.persistence.repositories.fin_daily_basic_repo import (
        FinDailyBasicRepository,
    )
    return FinDailyBasicRepository()


def get_fin_report_repository():
    from contexts.collect.infrastructure.persistence.repositories.fin_report_repo import (
        FinReportRepository,
    )
    return FinReportRepository()


def get_fin_top10_holders_repository():
    from contexts.collect.infrastructure.persistence.repositories.fin_top10_holders_repo import (
        FinTop10HoldersRepository,
    )
    return FinTop10HoldersRepository()


def get_fin_top10_float_holders_repository():
    from contexts.collect.infrastructure.persistence.repositories.fin_top10_float_holders_repo import (
        FinTop10FloatHoldersRepository,
    )
    return FinTop10FloatHoldersRepository()


def get_stock_concept_repository():
    from contexts.collect.infrastructure.persistence.repositories.stock_concept_repo import (
        StockConceptRepository,
    )
    return StockConceptRepository()


# ═══════════════════════════════════════════════════════════════════════
# concept 4
# ═══════════════════════════════════════════════════════════════════════
def get_concept_repository():
    from contexts.collect.infrastructure.persistence.repositories.concept_repo import (
        ConceptRepository,
    )
    return ConceptRepository()


def get_concept_member_repository():
    from contexts.collect.infrastructure.persistence.repositories.concept_member_repo import (
        ConceptMemberRepository,
    )
    return ConceptMemberRepository()


def get_concept_index_repository():
    from contexts.collect.infrastructure.persistence.repositories.concept_index_repo import (
        ConceptIndexRepository,
    )
    return ConceptIndexRepository()


def get_concept_snapshot_repository():
    from contexts.collect.infrastructure.persistence.repositories.concept_snapshot_repo import (
        ConceptSnapshotRepository,
    )
    return ConceptSnapshotRepository()


# ═══════════════════════════════════════════════════════════════════════
# news 1
# ═══════════════════════════════════════════════════════════════════════
def get_news_article_repository():
    from contexts.collect.infrastructure.persistence.repositories.news_article_repo import (
        NewsArticleRepository,
    )
    return NewsArticleRepository()


__all__ = [
    # tech
    "get_kline_repository", "get_stock_info_repository",
    "get_daily_kline_repository", "get_trade_calendar_repository",
    "get_stock_name_repository",
    "get_adj_factor_repository", "get_suspend_repository",
    "get_name_change_repository", "get_dividend_repository",
    # capital
    "get_moneyflow_repository", "get_moneyflow_hsgt_repository",
    "get_top_list_repository", "get_top_inst_repository",
    "get_block_trade_repository", "get_margin_detail_repository",
    "get_hsgt_top10_repository", "get_limit_list_repository",
    "get_holder_number_repository",
    # fundamental
    "get_fin_daily_basic_repository", "get_fin_report_repository",
    "get_fin_top10_holders_repository", "get_fin_top10_float_holders_repository",
    "get_stock_concept_repository",
    # concept
    "get_concept_repository", "get_concept_member_repository",
    "get_concept_index_repository", "get_concept_snapshot_repository",
    # news
    "get_news_article_repository",
]
