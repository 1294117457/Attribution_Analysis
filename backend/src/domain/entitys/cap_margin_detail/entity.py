"""cap_margin_detail — 领域实体"""

from dataclasses import dataclass
from typing import Optional

from domain.base import SymboledDatedEntity


@dataclass
class CapMarginDetail(SymboledDatedEntity):
    """两融明细（按个股）"""

    rzye: Optional[float] = None
    rqye: Optional[float] = None
    rzmre: Optional[float] = None
    rqyl: Optional[float] = None
    rzche: Optional[float] = None
    rqchl: Optional[float] = None
    rqmcl: Optional[float] = None
    rzrqye: Optional[float] = None
