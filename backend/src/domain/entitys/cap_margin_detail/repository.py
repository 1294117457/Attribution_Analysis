# TODO: DDD 仓储接口已定义，待 infrastructure 层实现对应 *_repo_impl
"""cap_margin_detail — 仓储接口"""

from domain.entitys.cap_margin_detail.entity import CapMarginDetail
from domain.repository import BaseSymboledDatedRepository


class CapMarginDetailRepository(BaseSymboledDatedRepository[CapMarginDetail]):
    """两融明细仓储（继承通用维度仓储）"""
    pass
