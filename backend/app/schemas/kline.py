"""K线数据 Schema"""

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class KLineResponse(BaseModel):
    """K线响应模型"""

    model_config = ConfigDict(from_attributes=True)

    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    date: date = Field(..., description="交易日期")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: float = Field(..., description="成交量(手)")
    amount: float = Field(..., description="成交额(元)")
    change_pct: Optional[float] = Field(None, description="涨跌幅(%)")
    turnover_rate: Optional[float] = Field(None, description="换手率(%)")


class KLineQueryRequest(BaseModel):
    """K线查询请求"""

    symbol: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="股票代码，6位数字",
        examples=["600519", "000858"],
    )
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "600519",
                "start_date": "2026-01-01",
                "end_date": "2026-06-25",
            }
        }
    )


class KLineListResponse(BaseModel):
    """K线列表响应"""

    total: int = Field(..., description="总条数")
    data: List[KLineResponse] = Field(..., description="K线数据列表")
