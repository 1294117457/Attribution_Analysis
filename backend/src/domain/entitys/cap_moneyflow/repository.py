"""cap_moneyflow — 仓储接口"""

from domain.entitys.cap_moneyflow.entity import CapMoneyflow
from domain.repository import BaseSymboledDatedRepository


class CapMoneyflowRepository(BaseSymboledDatedRepository[CapMoneyflow]):
    """资金流向仓储（继承通用维度仓储）"""
    pass
