"""仓储实现 - 统一导出

按照开发指南 §3 章节组织，每个子模块对应一个仓储实现类。

已实现：
- KlineRepoImpl         ← tech_kline_dailys 表
- StockRepoImpl         ← stock_infos 表
- StockPoolRepoImpl     ← stock_pools / stock_pool_members 表
- PoolOperationRepoImpl ← pool_operations 表

待实现（根据开发指南 §3 目录结构）：
- CapMoneyflowRepoImpl
- CapMarginDetailRepoImpl
- CapTopListRepoImpl
- CapTopInstRepoImpl
- CapBlockTradeRepoImpl
- CapHolderNumRepoImpl
- FinTop10HolderRepoImpl
- FinTop10FloatRepoImpl
- BaseAdjFactorRepoImpl
- BaseDividendRepoImpl
- BaseSuspendRepoImpl
- BaseNameChangeRepoImpl
- FinReportRepoImpl
- FinDailyBasicRepoImpl
- MktCalendarRepoImpl
- MktMarketDailyRepoImpl
- MktSectorDailyRepoImpl
- MktIndexMemberRepoImpl
"""

# ── 已实现的仓储 ──────────────────────────────────────────────────────────────

from infrastructure.repositories.kline_repository import KlineRepoImpl
from infrastructure.repositories.stock_repository import StockRepoImpl
from infrastructure.repositories.pool_repository import StockPoolRepoImpl
from infrastructure.repositories.pool_operation_repository import PoolOperationRepoImpl
from infrastructure.repositories.fin_daily_basic_repository import FinDailyBasicRepoImpl

# ── __all__ ────────────────────────────────────────────────────────────────────

__all__ = [
    # 已实现
    "KlineRepoImpl",
    "StockRepoImpl",
    "StockPoolRepoImpl",
    "PoolOperationRepoImpl",
    "FinDailyBasicRepoImpl",
    # 待实现（按开发指南 §3 顺序）
    # "CapMoneyflowRepoImpl",
    # "CapMarginDetailRepoImpl",
    # "CapTopListRepoImpl",
    # "CapTopInstRepoImpl",
    # "CapBlockTradeRepoImpl",
    # "CapHolderNumRepoImpl",
    # "FinTop10HolderRepoImpl",
    # "FinTop10FloatRepoImpl",
    # "BaseAdjFactorRepoImpl",
    # "BaseDividendRepoImpl",
    # "BaseSuspendRepoImpl",
    # "BaseNameChangeRepoImpl",
    # "FinReportRepoImpl",
    # "FinDailyBasicRepoImpl",
    # "MktCalendarRepoImpl",
    # "MktMarketDailyRepoImpl",
    # "MktSectorDailyRepoImpl",
    # "MktIndexMemberRepoImpl",
]
