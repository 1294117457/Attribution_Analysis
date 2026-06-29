"""
采集模块的数据模型。
"""

from pydantic import BaseModel
from typing import Optional
from datetime import date


class KLineRecord(BaseModel):
    """K线数据记录"""
    code: str
    name: str
    date: str  # YYYY-MM-DD
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    change_pct: Optional[float] = None
    turnover_rate: Optional[float] = None


class StockInfo(BaseModel):
    """股票基本信息"""
    code: str
    name: str
    industry: Optional[str] = None
    market: Optional[str] = None
    list_date: Optional[str] = None


class CollectionResult(BaseModel):
    """采集结果"""
    code: str
    name: str
    collected: int
    saved: int
    success: bool
    error: Optional[str] = None


class BatchCollectionResult(BaseModel):
    """批量采集结果"""
    total: int
    success: int
    failed: int
    total_collected: int
    total_saved: int
    results: list[CollectionResult]
