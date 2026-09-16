"""base_adj_factor — 领域 Schema"""

from datetime import date

from pydantic import BaseModel


class BaseAdjFactorBO(BaseModel):
    symbol: str
    trade_date: date
    adj_factor: float

    def to_entity(self) -> "BaseAdjFactor":
        from domain.base_adj_factor.entity import BaseAdjFactor
        return BaseAdjFactor(**self.model_dump())


class BaseAdjFactorVO(BaseModel):
    symbol: str
    trade_date: date
    adj_factor: float
