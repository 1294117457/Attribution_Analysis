"""股票应用层 DTO"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class StockUpdateRequest(BaseModel):
    """更新股票信息请求"""
    name: Optional[str] = None
    industry: Optional[str] = None
    market: Optional[str] = None


class StockUpsertRequest(BaseModel):
    """新增/更新股票请求"""
    symbol: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    industry: Optional[str] = None
    market: Optional[str] = None


class StockItemResponse(BaseModel):
    """股票详情响应"""
    symbol: str
    name: Optional[str] = None
    industry: Optional[str] = None
    market: Optional[str] = None
    list_date: Optional[date] = None
    total_shares: Optional[int] = None


class StockListItemResponse(BaseModel):
    """股票列表项（含K线统计）"""
    symbol: str
    name: Optional[str] = None
    industry: Optional[str] = None
    market: Optional[str] = None
    record_count: int = 0
    kline_start: Optional[date] = None
    kline_end: Optional[date] = None


class StockListResponse(BaseModel):
    """股票列表响应"""
    total: int
    items: list[StockListItemResponse]


class StockDeleteResponse(BaseModel):
    """删除股票响应"""
    symbol: str
    deleted_count: int
    message: str
