"""mkt_index_member — 领域 Schema"""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class MktIndexMemberBO(BaseModel):
    sector_type: str
    sector_code: str
    symbol: str
    sector_name: Optional[str] = None
    name: Optional[str] = None
    effective_date: Optional[date] = None
    expiry_date: Optional[date] = None
    is_new: Optional[str] = None

    def to_entity(self) -> "MktIndexMember":
        from domain.mkt_index_member.entity import MktIndexMember
        return MktIndexMember(**self.model_dump())


class MktIndexMemberVO(BaseModel):
    sector_type: str
    sector_code: str
    sector_name: Optional[str] = None
    symbol: str
    name: Optional[str] = None
    effective_date: Optional[date] = None
    is_new: Optional[str] = None
