"""Tushare：Client + 16 个 Adapter"""
from infrastructure.adapter.data.tushare.capital import (
    TushareBlockTradeAdapter,
    TushareHolderNumberAdapter,
    TushareMarginDetailAdapter,
    TushareMoneyflowAdapter,
    TushareTopInstAdapter,
    TushareTopListAdapter,
)
from infrastructure.adapter.data.tushare.client import TushareClient
from infrastructure.adapter.data.tushare.fundamental import (
    TushareDailyBasicAdapter,
    TushareFinIncomeAdapter,
    TushareTop10FloatHoldersAdapter,
    TushareTop10HoldersAdapter,
)
from infrastructure.adapter.data.tushare.reference import (
    TushareAdjFactorAdapter,
    TushareDividendAdapter,
    TushareNameChangeAdapter,
    TushareStockBasicAdapter,
    TushareSuspendAdapter,
)
from infrastructure.adapter.data.tushare.tech import TushareDailyKlineAdapter

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
