"""Tushare：Client + 16 个 Adapter"""
from contexts.data.infrastructure.adapter.tushare.capital import (
    TushareBlockTradeAdapter,
    TushareHolderNumberAdapter,
    TushareMarginDetailAdapter,
    TushareMoneyflowAdapter,
    TushareTopInstAdapter,
    TushareTopListAdapter,
)
from contexts.data.infrastructure.adapter.tushare.client import TushareClient
from contexts.data.infrastructure.adapter.tushare.fundamental import (
    TushareDailyBasicAdapter,
    TushareFinIncomeAdapter,
    TushareTop10FloatHoldersAdapter,
    TushareTop10HoldersAdapter,
)
from contexts.data.infrastructure.adapter.tushare.reference import (
    TushareAdjFactorAdapter,
    TushareDividendAdapter,
    TushareNameChangeAdapter,
    TushareStockBasicAdapter,
    TushareSuspendAdapter,
)
from contexts.data.infrastructure.adapter.tushare.tech import TushareDailyKlineAdapter

ADAPTERS = (
    TushareDailyKlineAdapter,
    TushareStockBasicAdapter,
    TushareDailyBasicAdapter,
    TushareFinIncomeAdapter,
    TushareMoneyflowAdapter,
    TushareMarginDetailAdapter,
    TushareTopListAdapter,
    TushareTopInstAdapter,
    TushareBlockTradeAdapter,
    TushareHolderNumberAdapter,
    TushareTop10HoldersAdapter,
    TushareTop10FloatHoldersAdapter,
    TushareAdjFactorAdapter,
    TushareSuspendAdapter,
    TushareNameChangeAdapter,
    TushareDividendAdapter,
)

__all__ = ["ADAPTERS", "TushareClient"]
