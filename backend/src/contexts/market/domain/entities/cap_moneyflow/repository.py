# TODO: DDD 仓储接口已定义，待 infrastructure 层实现对应 *_repo_impl
"""cap_moneyflow — 仓储接口"""

from contexts.market.domain.entities.cap_moneyflow.entity import CapMoneyflow
from shared.domain.repository import BaseSymboledDatedRepository


class CapMoneyflowRepository(BaseSymboledDatedRepository[CapMoneyflow]):
    """资金流向仓储（继承通用维度仓储）"""
    pass
