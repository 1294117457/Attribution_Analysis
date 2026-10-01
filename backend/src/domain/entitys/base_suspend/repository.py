# TODO: DDD 仓储接口已定义，待 infrastructure 层实现对应 *_repo_impl
"""base_suspend — 仓储接口"""

from domain.entitys.base_suspend.entity import BaseSuspend
from domain.repository import BaseSymboledDatedRepository


class BaseSuspendRepository(BaseSymboledDatedRepository[BaseSuspend]):
    """停复牌仓储（继承通用维度仓储）"""
    pass
