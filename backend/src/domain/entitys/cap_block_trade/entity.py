"""cap_block_trade — 领域实体"""

from dataclasses import dataclass
from typing import Optional

from domain.base import SymboledDatedEntity


@dataclass
class CapBlockTrade(SymboledDatedEntity):
    """大宗交易"""

    name: Optional[str] = None
    price: Optional[float] = None
    vol: Optional[float] = None
    amount: Optional[float] = None
    buyer: Optional[str] = None
    seller: Optional[str] = None
