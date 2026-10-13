"""K线 DTO（请求 + BO）— 来自 application/dto/kline.py 拆分"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


# ── 请求 DTO ──────────────────────────────────────────────────────────


class KlineCollectRequest(BaseModel):
    """采集K线请求"""
    symbol: str = Field(..., description="股票代码", examples=["000001"])
    days: int = Field(365, ge=1, le=3650, description="回溯天数")
    start_date: Optional[date] = Field(None, description="起始日期")
    end_date: Optional[date] = Field(None, description="结束日期")


class KlineQueryRequest(BaseModel):
    """查询K线请求"""
    symbol: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    limit: int = Field(365, ge=1, le=3650)
    order_desc: bool = True


class KlineDeleteRequest(BaseModel):
    """删除K线请求"""
    symbol: str
    trade_date: Optional[date] = None
