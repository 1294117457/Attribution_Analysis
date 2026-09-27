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


# ── BO（采集层 → 应用层） ─────────────────────────────────────────────


class KlineBO(BaseModel):
    """K线采集层 BO（由 fetcher/parser 输出，应用层消费）

    字段与 kline 聚合 entity.py 字段一一对应；
    fetcher 在此处做归一化（指标列填充、字段标准化）后传给 AppService。
    """
    symbol: str = Field(..., description="股票代码")
    trade_date: date = Field(..., description="交易日")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: int = Field(..., ge=0, description="成交量（股）")
    amount: float = Field(..., ge=0.0, description="成交额（元）")
    change_pct: Optional[float] = Field(default=None, description="涨跌幅 %")
    name: Optional[str] = Field(default=None, description="股票名称（可选）")
    source: str = Field(default="tushare", description="数据源")

    model_config = {"from_attributes": True}

    def to_entity_args(self) -> dict:
        """返回用于 Kline.create(**) 的字段；entity 层负责指标计算与持久化。"""
        return {
            "symbol": self.symbol,
            "trade_date": self.trade_date,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "amount": self.amount,
            "change_pct": self.change_pct,
            "name": self.name or self.symbol,
            "source": self.source,
        }
