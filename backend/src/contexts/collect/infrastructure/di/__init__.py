"""collect context — 业务 DI 工厂

collect 下 28 个 service 的 Depends 工厂都集中在 collect_service.py。
"""
from contexts.collect.infrastructure.di.collect_service import (
    # tech 5
    get_adj_factor_service,
    get_daily_service,
    get_minute_service,
    get_name_change_service,
    get_suspend_service,
    # capital 9
    get_block_trade_service,
    get_holder_number_service,
    get_hsgt_top10_service,
    get_limit_list_service,
    get_margin_service,
    get_moneyflow_hsgt_service,
    get_moneyflow_service,
    get_top_inst_service,
    get_top_list_service,
    # fundamental 12
    get_concept_index_daily_service,
    get_concept_list_service,
    get_concept_members_service,
    get_concept_minute_service,
    get_concept_snapshot_service,
    get_daily_basic_service,
    get_dividend_service,
    get_fin_income_service,
    get_stock_basic_service,
    get_stock_concepts_service,
    get_top10_float_holders_service,
    get_top10_holders_service,
    # news 1
    get_news_service,
    # sentiment 1
    get_sentiment_service,
)

__all__ = [
    # tech 5
    "get_adj_factor_service",
    "get_daily_service",
    "get_minute_service",
    "get_name_change_service",
    "get_suspend_service",
    # capital 9
    "get_block_trade_service",
    "get_holder_number_service",
    "get_hsgt_top10_service",
    "get_limit_list_service",
    "get_margin_service",
    "get_moneyflow_hsgt_service",
    "get_moneyflow_service",
    "get_top_inst_service",
    "get_top_list_service",
    # fundamental 12
    "get_concept_index_daily_service",
    "get_concept_list_service",
    "get_concept_members_service",
    "get_concept_minute_service",
    "get_concept_snapshot_service",
    "get_daily_basic_service",
    "get_dividend_service",
    "get_fin_income_service",
    "get_stock_basic_service",
    "get_stock_concepts_service",
    "get_top10_float_holders_service",
    "get_top10_holders_service",
    # news 1
    "get_news_service",
    # sentiment 1
    "get_sentiment_service",
]
