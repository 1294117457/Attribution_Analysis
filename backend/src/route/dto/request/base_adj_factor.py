"""自动迁移自 domain/base_adj_factor/schemas.py（BO 部分）"""

from __future__ import annotations

from pydantic import BaseModel
from datetime import date


class BaseAdjFactorBO(BaseModel):
    symbol: str
    trade_date: date
    adj_factor: float

    def to_entity(self) -> "BaseAdjFactor":
        from domain.entitys.base_adj_factor.entity import BaseAdjFactor
        return BaseAdjFactor(**self.model_dump())