"""fin_top10_float — 仓储接口"""

from domain.entitys.fin_top10_float.entity import FinTop10Float
from domain.repository import BaseSymboledDatedRepository


class FinTop10FloatRepository(BaseSymboledDatedRepository[FinTop10Float]):
    """前十大流通股东仓储（继承通用维度仓储）"""
    pass
