"""fin_daily_basic — 仓储接口"""

from contexts.market.domain.entities.fin_daily_basic.entity import FinDailyBasic
from shared.domain.repository import BaseSymboledDatedRepository


class FinDailyBasicRepository(BaseSymboledDatedRepository[FinDailyBasic]):
    """日频估值仓储（继承通用维度仓储）"""
    pass
