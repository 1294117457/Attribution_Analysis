"""K线数据 Schema"""

from pydantic import Field
from datetime import date
from typing import Optional

from data.schemas.base import BaseData


class DailyKline(BaseData):
    """日K线数据"""

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


class StockInfo(BaseData):
    """股票基本信息"""

    symbol: str
    name: str
    industry: Optional[str] = None
    market: Optional[str] = None
    list_date: Optional[date] = None
