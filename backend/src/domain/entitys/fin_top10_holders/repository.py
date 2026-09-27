"""fin_top10_holders — 仓储接口"""

from domain.entitys.fin_top10_holders.entity import FinTop10Holders
from domain.repository import BaseSymboledDatedRepository


class FinTop10HoldersRepository(BaseSymboledDatedRepository[FinTop10Holders]):
    """前十大股东仓储（继承通用维度仓储）"""
    pass
