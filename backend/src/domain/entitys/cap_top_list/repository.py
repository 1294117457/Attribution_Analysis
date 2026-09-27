"""cap_top_list — 仓储接口"""

from domain.entitys.cap_top_list.entity import CapTopList
from domain.repository import BaseSymboledDatedRepository


class CapTopListRepository(BaseSymboledDatedRepository[CapTopList]):
    """龙虎榜汇总仓储（继承通用维度仓储）"""
    pass
