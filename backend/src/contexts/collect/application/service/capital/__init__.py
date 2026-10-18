"""capital — 资金面 service 集合（9 个）"""
from contexts.collect.application.service.capital.moneyflow_service import MoneyflowService
from contexts.collect.application.service.capital.moneyflow_hsgt_service import MoneyflowHsgtService
from contexts.collect.application.service.capital.top_list_service import TopListService
from contexts.collect.application.service.capital.top_inst_service import TopInstService
from contexts.collect.application.service.capital.block_trade_service import BlockTradeService
from contexts.collect.application.service.capital.margin_service import MarginService
from contexts.collect.application.service.capital.hsgt_top10_service import HsgtTop10Service
from contexts.collect.application.service.capital.limit_list_service import LimitListService
from contexts.collect.application.service.capital.holder_number_service import HolderNumberService

__all__ = [
    "MoneyflowService",
    "MoneyflowHsgtService",
    "TopListService",
    "TopInstService",
    "BlockTradeService",
    "MarginService",
    "HsgtTop10Service",
    "LimitListService",
    "HolderNumberService",
]
