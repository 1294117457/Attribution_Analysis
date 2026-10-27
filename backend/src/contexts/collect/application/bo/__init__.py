"""BO 汇总（兼容旧 _port_models，按 facet 分子文件）

BO = Business Object，外部数据进入系统时的 Pydantic 载体；
由 fetcher.fetch() 返回，由 service 转 entity。
"""

from contexts.collect.application.bo.tech import (
    BaseAdjFactorBO,
    BaseDividendBO,
    BaseNameChangeBO,
    BaseSuspendBO,
    DailyFetcherResult,
)
from contexts.collect.application.bo.capital import (
    CapBlockTradeBO,
    CapHolderNumBO,
    CapHsgtTop10BO,                  # §1.4
    CapLimitListDBO,                 # §1.3
    CapMarginDetailBO,
    CapMoneyflowBO,
    CapMoneyflowHsgtBO,              # §1.2
    CapTopInstBO,
    CapTopListBO,
)
from contexts.collect.application.bo.fundamental import (
    FinDailyBasicBO,
    FinReportBO,
    FinTop10FloatHoldersBO,
    FinTop10HoldersBO,
)

__all__ = [
    # tech
    "BaseAdjFactorBO", "BaseSuspendBO", "BaseNameChangeBO", "BaseDividendBO",
    "DailyFetcherResult",
    # capital
    "CapMoneyflowBO", "CapMoneyflowHsgtBO", "CapHsgtTop10BO", "CapLimitListDBO",
    "CapMarginDetailBO", "CapTopListBO", "CapTopInstBO",
    "CapBlockTradeBO", "CapHolderNumBO",
    # fundamental
    "FinDailyBasicBO", "FinReportBO",
    "FinTop10HoldersBO", "FinTop10FloatHoldersBO",
]
