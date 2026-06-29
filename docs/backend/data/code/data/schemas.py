"""数据采集模块的 Pydantic 模型"""

from pydantic import BaseModel, Field
from datetime import date
from typing import Optional


class StockKline(BaseModel):
    """K 线数据"""

    symbol: str = Field(..., description="股票代码")
    name: str = Field("", description="股票名称")
    date: date = Field(..., description="日期")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: int = Field(..., description="成交量")
    amount: float = Field(..., description="成交额")
    change_pct: Optional[float] = Field(None, description="涨跌幅 %")


class StockKlineResponse(BaseModel):
    """K 线数据响应"""

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


class StockListResponse(BaseModel):
    """股票列表响应"""

    total: int
    items: list[StockKlineResponse]


class CollectResponse(BaseModel):
    """采集响应"""

    status: str  # success, failed, partial
    symbol: str
    count: int
    message: str
