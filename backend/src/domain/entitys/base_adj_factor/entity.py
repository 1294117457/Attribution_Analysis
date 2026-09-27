"""base_adj_factor — 领域实体"""

from dataclasses import dataclass

from domain.base import SymboledDatedEntity


@dataclass
class BaseAdjFactor(SymboledDatedEntity):
    """复权因子"""

    adj_factor: float = 0.0
