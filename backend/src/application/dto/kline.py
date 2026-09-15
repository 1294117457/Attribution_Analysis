"""K线应用层 DTO"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


# ── 请求 DTO ──────────────────────────────────────────────

class KlineCollectRequest(BaseModel):
    """采集K线请求"""
    symbol: str = Field(..., description="股票代码", examples=["000001"])
    days: int = Field(365, ge=1, le=3650, description="回溯天数")
    start_date: Optional[date] = Field(None, description="开始日期")
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


# ── 响应 DTO ──────────────────────────────────────────────

class KlineItemResponse(BaseModel):
    """单条K线响应"""
    symbol: str
    name: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    change_pct: Optional[float] = None


class KlineListResponse(BaseModel):
    """K线列表响应"""
    total: int
    items: list[KlineItemResponse]


class KlineCollectResponse(BaseModel):
    """K线采集响应"""
    symbol: str
    name: str
    saved_count: int
    total_count: int
    message: str


class KlineDeleteResponse(BaseModel):
    """K线删除响应"""
    symbol: str
    deleted_count: int
    message: str


class KlineStatsResponse(BaseModel):
    """K线统计响应"""
    symbol: str
    name: str
    count: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    latest_close: Optional[float] = None
    latest_volume: Optional[int] = None
