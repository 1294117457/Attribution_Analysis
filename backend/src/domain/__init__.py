"""领域层 - 统一导出

按照开发指南 §2 章节组织，每个子模块导出：
- entity: 领域实体（聚合根/实体）
- repository: 仓储接口（ABC）
- schemas: BO (Business Object 采集层) / VO (View Object API 出参)
"""

# ── kline ──────────────────────────────────────────────────────────────────────

from domain.kline.entity import Kline
from domain.kline.repository import KlineRepository
from domain.kline.schemas import KlineBO, KlineVO, KlineStatsVO
from domain.kline.value_objects import StockCode

# ── stock_info ─────────────────────────────────────────────────────────────────

from domain.stock_info.entity import StockInfo
from domain.stock_info.repository import StockInfoRepository
from domain.stock_info.schemas import (
    StockInfoBO,
    StockInfoVO,
    StockListItemVO,
    StockMetaVO,
    SyncResultVO,
)

# ── stock_pool ─────────────────────────────────────────────────────────────────

from domain.stock_pool.entity import StockPool
from domain.stock_pool.value_objects import PoolMember
from domain.stock_pool.repository import StockPoolRepository, PoolOperationRepository
from domain.stock_pool.schemas import (
    StockPoolVO,
    StockPoolDetailVO,
    StockPoolCreateBO,
    StockPoolUpdateBO,
    PoolMemberVO,
    PoolOperationVO,
)

# ── fin_report ─────────────────────────────────────────────────────────────────

from domain.fin_report.entity import FinReport
from domain.fin_report.repository import FinReportRepository
from domain.fin_report.schemas import FinReportBO, FinReportVO

# ── fin_daily_basic ────────────────────────────────────────────────────────────

from domain.fin_daily_basic.entity import FinDailyBasic
from domain.fin_daily_basic.repository import FinDailyBasicRepository
from domain.fin_daily_basic.schemas import FinDailyBasicBO, FinDailyBasicVO

# ── cap_margin ────────────────────────────────────────────────────────────────

from domain.cap_margin.entity import CapMargin
from domain.cap_margin.repository import CapMarginRepository
from domain.cap_margin.schemas import CapMarginBO, CapMarginVO

# ── cap_moneyflow ─────────────────────────────────────────────────────────────

from domain.cap_moneyflow.entity import CapMoneyflow
from domain.cap_moneyflow.repository import CapMoneyflowRepository
from domain.cap_moneyflow.schemas import CapMoneyflowBO, CapMoneyflowVO

# ── cap_margin_detail ─────────────────────────────────────────────────────────

from domain.cap_margin_detail.entity import CapMarginDetail
from domain.cap_margin_detail.repository import CapMarginDetailRepository
from domain.cap_margin_detail.schemas import CapMarginDetailBO, CapMarginDetailVO

# ── cap_top_list ─────────────────────────────────────────────────────────────

from domain.cap_top_list.entity import CapTopList
from domain.cap_top_list.repository import CapTopListRepository
from domain.cap_top_list.schemas import CapTopListBO, CapTopListVO

# ── cap_top_inst ─────────────────────────────────────────────────────────────

from domain.cap_top_inst.entity import CapTopInst
from domain.cap_top_inst.repository import CapTopInstRepository
from domain.cap_top_inst.schemas import CapTopInstBO, CapTopInstVO

# ── cap_block_trade ───────────────────────────────────────────────────────────

from domain.cap_block_trade.entity import CapBlockTrade
from domain.cap_block_trade.repository import CapBlockTradeRepository
from domain.cap_block_trade.schemas import CapBlockTradeBO, CapBlockTradeVO

# ── cap_holder_num ────────────────────────────────────────────────────────────

from domain.cap_holder_num.entity import CapHolderNum
from domain.cap_holder_num.repository import CapHolderNumRepository
from domain.cap_holder_num.schemas import CapHolderNumBO, CapHolderNumVO

# ── fin_top10_holders ─────────────────────────────────────────────────────────

from domain.fin_top10_holders.entity import FinTop10Holder
from domain.fin_top10_holders.repository import FinTop10HolderRepository
from domain.fin_top10_holders.schemas import FinTop10HolderBO, FinTop10HolderVO

# ── fin_top10_float ───────────────────────────────────────────────────────────

from domain.fin_top10_float.entity import FinTop10FloatHolder
from domain.fin_top10_float.repository import FinTop10FloatHolderRepository
from domain.fin_top10_float.schemas import FinTop10FloatHolderBO, FinTop10FloatHolderVO

# ── base_adj_factor ──────────────────────────────────────────────────────────

from domain.base_adj_factor.entity import BaseAdjFactor
from domain.base_adj_factor.repository import BaseAdjFactorRepository
from domain.base_adj_factor.schemas import BaseAdjFactorBO, BaseAdjFactorVO

# ── base_dividend ────────────────────────────────────────────────────────────

from domain.base_dividend.entity import BaseDividend
from domain.base_dividend.repository import BaseDividendRepository
from domain.base_dividend.schemas import BaseDividendBO, BaseDividendVO

# ── base_suspend ─────────────────────────────────────────────────────────────

from domain.base_suspend.entity import BaseSuspend
from domain.base_suspend.repository import BaseSuspendRepository
from domain.base_suspend.schemas import BaseSuspendBO, BaseSuspendVO

# ── base_name_change ─────────────────────────────────────────────────────────

from domain.base_name_change.entity import BaseNameChange
from domain.base_name_change.repository import BaseNameChangeRepository
from domain.base_name_change.schemas import BaseNameChangeBO, BaseNameChangeVO

# ── mkt_calendar ─────────────────────────────────────────────────────────────

from domain.mkt_calendar.entity import MktCalendar
from domain.mkt_calendar.repository import MktCalendarRepository
from domain.mkt_calendar.schemas import MktCalendarBO, MktCalendarVO

# ── mkt_market_daily ──────────────────────────────────────────────────────────

from domain.mkt_market_daily.entity import MktMarketDaily
from domain.mkt_market_daily.repository import MktMarketDailyRepository
from domain.mkt_market_daily.schemas import MktMarketDailyBO, MktMarketDailyVO

# ── mkt_sector_daily ─────────────────────────────────────────────────────────

from domain.mkt_sector_daily.entity import MktSectorDaily
from domain.mkt_sector_daily.repository import MktSectorDailyRepository
from domain.mkt_sector_daily.schemas import MktSectorDailyBO, MktSectorDailyVO

# ── mkt_index_member ──────────────────────────────────────────────────────────

from domain.mkt_index_member.entity import MktIndexMember
from domain.mkt_index_member.repository import MktIndexMemberRepository
from domain.mkt_index_member.schemas import MktIndexMemberBO, MktIndexMemberVO


# ── 全模块 __all__ ────────────────────────────────────────────────────────────

__all__ = [
    # ── kline ──────────────────────────────────────────────────────────────
    "Kline",
    "KlineRepository",
    "KlineBO",
    "KlineVO",
    "KlineStatsVO",
    "StockCode",
    # ── stock_info ─────────────────────────────────────────────────────────
    "StockInfo",
    "StockInfoRepository",
    "StockInfoBO",
    "StockInfoVO",
    "StockListItemVO",
    "StockMetaVO",
    "SyncResultVO",
    # ── stock_pool ─────────────────────────────────────────────────────────
    "StockPool",
    "PoolMember",
    "StockPoolRepository",
    "PoolOperationRepository",
    "StockPoolVO",
    "StockPoolDetailVO",
    "StockPoolCreateBO",
    "StockPoolUpdateBO",
    "PoolMemberVO",
    "PoolOperationVO",
    # ── fin_report ──────────────────────────────────────────────────────────
    "FinReport",
    "FinReportRepository",
    "FinReportBO",
    "FinReportVO",
    # ── fin_daily_basic ────────────────────────────────────────────────────
    "FinDailyBasic",
    "FinDailyBasicRepository",
    "FinDailyBasicBO",
    "FinDailyBasicVO",
    # ── cap_margin ─────────────────────────────────────────────────────────
    "CapMargin",
    "CapMarginRepository",
    "CapMarginBO",
    "CapMarginVO",
    # ── cap_moneyflow ──────────────────────────────────────────────────────
    "CapMoneyflow",
    "CapMoneyflowRepository",
    "CapMoneyflowBO",
    "CapMoneyflowVO",
    # ── cap_margin_detail ───────────────────────────────────────────────────
    "CapMarginDetail",
    "CapMarginDetailRepository",
    "CapMarginDetailBO",
    "CapMarginDetailVO",
    # ── cap_top_list ────────────────────────────────────────────────────────
    "CapTopList",
    "CapTopListRepository",
    "CapTopListBO",
    "CapTopListVO",
    # ── cap_top_inst ───────────────────────────────────────────────────────
    "CapTopInst",
    "CapTopInstRepository",
    "CapTopInstBO",
    "CapTopInstVO",
    # ── cap_block_trade ────────────────────────────────────────────────────
    "CapBlockTrade",
    "CapBlockTradeRepository",
    "CapBlockTradeBO",
    "CapBlockTradeVO",
    # ── cap_holder_num ────────────────────────────────────────────────────
    "CapHolderNum",
    "CapHolderNumRepository",
    "CapHolderNumBO",
    "CapHolderNumVO",
    # ── fin_top10_holders ─────────────────────────────────────────────────
    "FinTop10Holder",
    "FinTop10HolderRepository",
    "FinTop10HolderBO",
    "FinTop10HolderVO",
    # ── fin_top10_float ────────────────────────────────────────────────────
    "FinTop10FloatHolder",
    "FinTop10FloatHolderRepository",
    "FinTop10FloatHolderBO",
    "FinTop10FloatHolderVO",
    # ── base_adj_factor ────────────────────────────────────────────────────
    "BaseAdjFactor",
    "BaseAdjFactorRepository",
    "BaseAdjFactorBO",
    "BaseAdjFactorVO",
    # ── base_dividend ──────────────────────────────────────────────────────
    "BaseDividend",
    "BaseDividendRepository",
    "BaseDividendBO",
    "BaseDividendVO",
    # ── base_suspend ───────────────────────────────────────────────────────
    "BaseSuspend",
    "BaseSuspendRepository",
    "BaseSuspendBO",
    "BaseSuspendVO",
    # ── base_name_change ───────────────────────────────────────────────────
    "BaseNameChange",
    "BaseNameChangeRepository",
    "BaseNameChangeBO",
    "BaseNameChangeVO",
    # ── mkt_calendar ───────────────────────────────────────────────────────
    "MktCalendar",
    "MktCalendarRepository",
    "MktCalendarBO",
    "MktCalendarVO",
    # ── mkt_market_daily ──────────────────────────────────────────────────
    "MktMarketDaily",
    "MktMarketDailyRepository",
    "MktMarketDailyBO",
    "MktMarketDailyVO",
    # ── mkt_sector_daily ───────────────────────────────────────────────────
    "MktSectorDaily",
    "MktSectorDailyRepository",
    "MktSectorDailyBO",
    "MktSectorDailyVO",
    # ── mkt_index_member ───────────────────────────────────────────────────
    "MktIndexMember",
    "MktIndexMemberRepository",
    "MktIndexMemberBO",
    "MktIndexMemberVO",
]
