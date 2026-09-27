"""领域层 - 统一导出（按 DDD.md：仅暴露 entity / repository / vo）"""

# ── kline ──────────────────────────────────────────────────────────────
from domain.entitys.kline.entity import Kline
from domain.entitys.kline.repository import KlineRepository
from domain.entitys.kline.vo import StockCode

# ── stock_info ─────────────────────────────────────────────────────────
from domain.entitys.stock_info.entity import StockInfo
from domain.entitys.stock_info.repository import StockInfoRepository

# ── stock_pool ─────────────────────────────────────────────────────────
from domain.entitys.stock_pool.entity import StockPool
from domain.entitys.stock_pool.repository import (
    PoolOperationRepository,
    StockPoolRepository,
)
from domain.entitys.stock_pool.vo import PoolMember

# ── fin_report ────────────────────────────────────────────────────────
from domain.entitys.fin_report.entity import FinReport
from domain.entitys.fin_report.repository import FinReportRepository

# ── fin_daily_basic ──────────────────────────────────────────────────
from domain.entitys.fin_daily_basic.entity import FinDailyBasic
from domain.entitys.fin_daily_basic.repository import FinDailyBasicRepository

# ── cap_margin ────────────────────────────────────────────────────────
from domain.entitys.cap_margin.entity import CapMargin
from domain.entitys.cap_margin.repository import CapMarginRepository

# ── cap_moneyflow ─────────────────────────────────────────────────────
from domain.entitys.cap_moneyflow.entity import CapMoneyflow
from domain.entitys.cap_moneyflow.repository import CapMoneyflowRepository

# ── cap_margin_detail ─────────────────────────────────────────────────
from domain.entitys.cap_margin_detail.entity import CapMarginDetail
from domain.entitys.cap_margin_detail.repository import CapMarginDetailRepository

# ── cap_top_list ──────────────────────────────────────────────────────
from domain.entitys.cap_top_list.entity import CapTopList
from domain.entitys.cap_top_list.repository import CapTopListRepository

# ── cap_top_inst ──────────────────────────────────────────────────────
from domain.entitys.cap_top_inst.entity import CapTopInst
from domain.entitys.cap_top_inst.repository import CapTopInstRepository

# ── cap_block_trade ───────────────────────────────────────────────────
from domain.entitys.cap_block_trade.entity import CapBlockTrade
from domain.entitys.cap_block_trade.repository import CapBlockTradeRepository

# ── cap_holder_num ───────────────────────────────────────────────────
from domain.entitys.cap_holder_num.entity import CapHolderNum
from domain.entitys.cap_holder_num.repository import CapHolderNumRepository

# ── fin_top10_holders ─────────────────────────────────────────────────
from domain.entitys.fin_top10_holders.entity import FinTop10Holders
from domain.entitys.fin_top10_holders.repository import FinTop10HoldersRepository

# ── fin_top10_float ───────────────────────────────────────────────────
from domain.entitys.fin_top10_float.entity import FinTop10Float
from domain.entitys.fin_top10_float.repository import FinTop10FloatRepository

# ── base_adj_factor ───────────────────────────────────────────────────
from domain.entitys.base_adj_factor.entity import BaseAdjFactor
from domain.entitys.base_adj_factor.repository import BaseAdjFactorRepository

# ── base_dividend ─────────────────────────────────────────────────────
from domain.entitys.base_dividend.entity import BaseDividend
from domain.entitys.base_dividend.repository import BaseDividendRepository

# ── base_suspend ──────────────────────────────────────────────────────
from domain.entitys.base_suspend.entity import BaseSuspend
from domain.entitys.base_suspend.repository import BaseSuspendRepository

# ── base_name_change ──────────────────────────────────────────────────
from domain.entitys.base_name_change.entity import BaseNameChange
from domain.entitys.base_name_change.repository import BaseNameChangeRepository

# ── mkt_calendar ─────────────────────────────────────────────────────
from domain.entitys.mkt_calendar.entity import MktCalendar
from domain.entitys.mkt_calendar.repository import MktCalendarRepository

# ── mkt_market_daily ──────────────────────────────────────────────────
from domain.entitys.mkt_market_daily.entity import MktMarketDaily
from domain.entitys.mkt_market_daily.repository import MktMarketDailyRepository

# ── mkt_sector_daily ─────────────────────────────────────────────────
from domain.entitys.mkt_sector_daily.entity import MktSectorDaily
from domain.entitys.mkt_sector_daily.repository import MktSectorDailyRepository

# ── mkt_index_member ──────────────────────────────────────────────────
from domain.entitys.mkt_index_member.entity import MktIndexMember
from domain.entitys.mkt_index_member.repository import MktIndexMemberRepository

# ── panel (cross-aggregate composition) ───────────────────────────────
from domain.entitys.panel.repository import StockPanelComposeRepository

__all__ = [
    # kline
    "Kline", "KlineRepository", "StockCode",
    # stock_info
    "StockInfo", "StockInfoRepository",
    # stock_pool
    "StockPool", "StockPoolRepository", "PoolOperationRepository", "PoolMember",
    # fin_report
    "FinReport", "FinReportRepository",
    # fin_daily_basic
    "FinDailyBasic", "FinDailyBasicRepository",
    # cap_margin
    "CapMargin", "CapMarginRepository",
    # cap_moneyflow
    "CapMoneyflow", "CapMoneyflowRepository",
    # cap_margin_detail
    "CapMarginDetail", "CapMarginDetailRepository",
    # cap_top_list
    "CapTopList", "CapTopListRepository",
    # cap_top_inst
    "CapTopInst", "CapTopInstRepository",
    # cap_block_trade
    "CapBlockTrade", "CapBlockTradeRepository",
    # cap_holder_num
    "CapHolderNum", "CapHolderNumRepository",
    # fin_top10_holders
    "FinTop10Holders", "FinTop10HoldersRepository",
    # fin_top10_float
    "FinTop10Float", "FinTop10FloatRepository",
    # base_adj_factor
    "BaseAdjFactor", "BaseAdjFactorRepository",
    # base_dividend
    "BaseDividend", "BaseDividendRepository",
    # base_suspend
    "BaseSuspend", "BaseSuspendRepository",
    # base_name_change
    "BaseNameChange", "BaseNameChangeRepository",
    # mkt_calendar
    "MktCalendar", "MktCalendarRepository",
    # mkt_market_daily
    "MktMarketDaily", "MktMarketDailyRepository",
    # mkt_sector_daily
    "MktSectorDaily", "MktSectorDailyRepository",
    # mkt_index_member
    "MktIndexMember", "MktIndexMemberRepository",
    # panel
    "StockPanelComposeRepository",
]
