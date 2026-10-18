"""BO 汇总（兼容旧 _port_models，按 facet 分子文件）

BO = Business Object，外部数据进入系统时的 Pydantic 载体；
由 fetcher.fetch() 返回，由 service 转 entity。
"""

from contexts.collect.application.bo.tech import (
    BaseAdjFactorBO,
    BaseDividendBO,
    BaseNameChangeBO,
    BaseSuspendBO,
)
from contexts.collect.application.bo.capital import (
    CapBlockTradeBO,
    CapHolderNumBO,
    CapMarginDetailBO,
    CapMoneyflowBO,
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
    # capital
    "CapMoneyflowBO", "CapMarginDetailBO", "CapTopListBO", "CapTopInstBO",
    "CapBlockTradeBO", "CapHolderNumBO",
    # fundamental
    "FinDailyBasicBO", "FinReportBO",
    "FinTop10HoldersBO", "FinTop10FloatHoldersBO",
]
