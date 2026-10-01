# TODO: DDD 仓储接口已定义，待 infrastructure 层实现对应 *_repo_impl
"""cap_block_trade — 仓储接口"""

from domain.entitys.cap_block_trade.entity import CapBlockTrade
from domain.repository import BaseSymboledDatedRepository


class CapBlockTradeRepository(BaseSymboledDatedRepository[CapBlockTrade]):
    """大宗交易仓储（继承通用维度仓储）"""
    pass
