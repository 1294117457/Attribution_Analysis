"""采集器注册表：28 个 collector 的唯一出口。

替代原 infrastructure/di/collect_service.py 的 28 个 get_*_service() 工厂函数。
service 全部无状态可直接构造，注册表只做 name -> class 映射。
"""
from __future__ import annotations

from collectors.tech.adj_factor_service import AdjFactorService
from collectors.tech.daily_kline_service import DailyKlineService
from collectors.tech.minute_kline_service import MinuteKlineService
from collectors.tech.name_change_service import NameChangeService
from collectors.tech.suspend_service import SuspendService
from collectors.capital.block_trade_service import BlockTradeService
from collectors.capital.holder_number_service import HolderNumberService
from collectors.capital.hsgt_top10_service import HsgtTop10Service
from collectors.capital.limit_list_service import LimitListService
from collectors.capital.margin_service import MarginService
from collectors.capital.moneyflow_hsgt_service import MoneyflowHsgtService
from collectors.capital.moneyflow_service import MoneyflowService
from collectors.capital.top_inst_service import TopInstService
from collectors.capital.top_list_service import TopListService
from collectors.fundamental.concept_index_daily_service import ConceptIndexDailyService
from collectors.fundamental.concept_list_service import ConceptListService
from collectors.fundamental.concept_members_service import ConceptMembersService
from collectors.fundamental.concept_minute_service import ConceptMinuteService
from collectors.fundamental.concept_snapshot_service import ConceptSnapshotService
from collectors.fundamental.daily_basic_service import DailyBasicService
from collectors.fundamental.dividend_service import DividendService
from collectors.fundamental.fin_income_service import FinIncomeService
from collectors.fundamental.stock_basic_service import StockBasicService
from collectors.fundamental.stock_concepts_service import StockConceptsService
from collectors.fundamental.top10_floatholders_service import Top10FloatHoldersService
from collectors.fundamental.top10_holders_service import Top10HoldersService
from collectors.news.news_service import NewsService
from collectors.sentiment.sentiment_service import SentimentService

SERVICES = [
    DailyKlineService, MinuteKlineService, AdjFactorService, SuspendService, NameChangeService,
    MoneyflowService, MoneyflowHsgtService, TopListService, TopInstService, BlockTradeService,
    MarginService, HsgtTop10Service, LimitListService, HolderNumberService,
    DailyBasicService, FinIncomeService, Top10HoldersService, Top10FloatHoldersService,
    DividendService, StockBasicService, StockConceptsService, ConceptListService,
    ConceptMembersService, ConceptIndexDailyService, ConceptMinuteService, ConceptSnapshotService,
    NewsService, SentimentService,
]

BY_NAME: dict[str, type] = {c.name: c for c in SERVICES}


def get(name: str):
    """按 name 取 service 实例（不存在抛 KeyError，上层转 404）。"""
    return BY_NAME[name]()


__all__ = ["SERVICES", "BY_NAME", "get"]
