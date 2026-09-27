"""自动迁移自 domain/kline/schemas.py（VO 部分）"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import date, datetime

class KlineVO(BaseModel):
    """K线视图对象（API 出参）

    注意：date 字段（不使用 trade_date），方便前端直接使用。
    """

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

    model_config = {"from_attributes": True}

    @classmethod
    def from_entity(cls, kline: Kline) -> "KlineVO":
        return cls(
            symbol=kline.symbol.code,
            name=kline.name,
            date=kline.trade_date.date,
            open=kline.open,
            high=kline.high,
            low=kline.low,
            close=kline.close,
            volume=kline.volume,
            amount=kline.amount,
            change_pct=kline.change_pct,
        )


class KlineStatsVO(BaseModel):
    """K线统计视图"""

    symbol: str
    name: str
    count: int = 0
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    latest_close: Optional[float] = None
    latest_volume: Optional[int] = None


class KlineItemResponse(BaseModel):
    """K线项响应（带指标列）"""
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

    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None
    ema12: Optional[float] = None
    ema26: Optional[float] = None
    macd_dif: Optional[float] = None
    macd_dea: Optional[float] = None
    macd_bar: Optional[float] = None
    rsi6: Optional[float] = None
    rsi12: Optional[float] = None
    rsi24: Optional[float] = None
    kdj_k: Optional[float] = None
    kdj_d: Optional[float] = None
    kdj_j: Optional[float] = None
    boll_up: Optional[float] = None
    boll_mid: Optional[float] = None
    boll_dn: Optional[float] = None


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
    """K线统计响应（同 KlineStatsVO）"""
    symbol: str
    name: str
    count: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    latest_close: Optional[float] = None
    latest_volume: Optional[int] = None
