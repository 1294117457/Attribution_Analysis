"""base_adj_factor — 仓储接口"""

from domain.entitys.base_adj_factor.entity import BaseAdjFactor
from domain.repository import BaseSymboledDatedRepository


class BaseAdjFactorRepository(BaseSymboledDatedRepository[BaseAdjFactor]):
    """复权因子仓储（继承通用维度仓储）"""
    pass
