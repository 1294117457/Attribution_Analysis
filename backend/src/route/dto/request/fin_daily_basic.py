"""自动迁移自 domain/fin_daily_basic/schemas.py（BO 部分）"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import date, datetime

class FinDailyBasicBO(BaseModel):
    symbol: str
    trade_date: date
    close: Optional[float] = None
    turnover_rate: Optional[float] = None
    turnover_rate_f: Optional[float] = None
    volume_ratio: Optional[float] = None
    pe: Optional[float] = None
    pe_ttm: Optional[float] = None
    pb: Optional[float] = None
    ps: Optional[float] = None
    ps_ttm: Optional[float] = None
    dv_ratio: Optional[float] = None
    dv_ttm: Optional[float] = None
    total_share: Optional[float] = None
    float_share: Optional[float] = None
    free_share: Optional[float] = None
    total_mv: Optional[float] = None
    circ_mv: Optional[float] = None

    def to_entity(self) -> "FinDailyBasic":
        from domain.entitys.fin_daily_basic.entity import FinDailyBasic
        return FinDailyBasic(**self.model_dump())


