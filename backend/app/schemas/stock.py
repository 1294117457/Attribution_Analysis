"""日K线 API Pydantic 模型"""

from pydantic import BaseModel, Field
from datetime import date
from typing import Optional


class DailyKlineResponse(BaseModel):
    """日K线响应"""

    id: int
    symbol: str
    name: Optional[str] = None
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    change_pct: Optional[float] = None

    class Config:
        from_attributes = True


class DailyKlineListResponse(BaseModel):
    """日K线列表响应"""

    total: int
    items: list[DailyKlineResponse]


class CollectRequest(BaseModel):
    """采集请求"""

    symbol: str = Field(..., description="股票代码，如 000001")
    days: int = Field(365, ge=1, le=3650, description="采集天数")
    start_date: Optional[date] = Field(None, description="开始日期（优先于 days）")
    end_date: Optional[date] = Field(None, description="结束日期")


class CollectResponse(BaseModel):
    """采集响应"""

    status: str
    symbol: str
    count: int
    message: str
