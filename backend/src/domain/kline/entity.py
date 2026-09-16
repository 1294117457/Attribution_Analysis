"""K线聚合根（含技术指标派生属性，方案 A）"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from domain.base import AggregateRoot
from domain.kline.value_objects import StockCode, TradeDate


@dataclass
class Kline(AggregateRoot):
    """K线聚合根

    业务规则：high >= low, high >= open, high >= close, low <= open, low <= close

    技术指标列（ma5/ma10/.../boll_dn）是 K 线的派生属性，基于历史 close 计算。
    """

    id: int
    symbol: StockCode
    trade_date: TradeDate
    name: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    change_pct: Optional[float] = None
    created_at: Optional[date] = None
    updated_at: Optional[date] = None

    # ── 技术指标（派生属性，可空）──────────────────────────
    ma5:  Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None
    ema12: Optional[float] = None
    ema26: Optional[float] = None
    macd_dif: Optional[float] = None
    macd_dea: Optional[float] = None
    macd_bar: Optional[float] = None
    rsi6:  Optional[float] = None
    rsi12: Optional[float] = None
    rsi24: Optional[float] = None
    kdj_k: Optional[float] = None
    kdj_d: Optional[float] = None
    kdj_j: Optional[float] = None
    boll_up:  Optional[float] = None
    boll_mid: Optional[float] = None
    boll_dn:  Optional[float] = None

    def __post_init__(self):
        # 调用父类初始化（设置 _domain_events 列表）
        AggregateRoot.__init__(self)

    @property
    def is_up(self) -> bool:
        return self.close > self.open

    @property
    def is_down(self) -> bool:
        return self.close < self.open

    @property
    def price_range(self) -> float:
        return self.high - self.low

    def validate(self) -> None:
        """业务规则验证"""
        errors = []
        if self.high < self.low:
            errors.append("最高价不能低于最低价")
        if self.high < self.open or self.high < self.close:
            errors.append("最高价不能低于开盘价或收盘价")
        if self.low > self.open or self.low > self.close:
            errors.append("最低价不能高于开盘价或收盘价")
        if self.volume < 0:
            errors.append("成交量不能为负")
        if self.amount < 0:
            errors.append("成交额不能为负")
        if errors:
            raise ValueError(f"K线数据验证失败: {'; '.join(errors)}")

    @classmethod
    def create(
        cls,
        symbol: str,
        name: str,
        trade_date: date,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        amount: float,
        change_pct: Optional[float] = None,
        # 指标字段（可选传入，采集时由 IndicatorCalculator 填充）
        ma5: Optional[float] = None,
        ma10: Optional[float] = None,
        ma20: Optional[float] = None,
        ma60: Optional[float] = None,
        ema12: Optional[float] = None,
        ema26: Optional[float] = None,
        macd_dif: Optional[float] = None,
        macd_dea: Optional[float] = None,
        macd_bar: Optional[float] = None,
        rsi6: Optional[float] = None,
        rsi12: Optional[float] = None,
        rsi24: Optional[float] = None,
        kdj_k: Optional[float] = None,
        kdj_d: Optional[float] = None,
        kdj_j: Optional[float] = None,
        boll_up: Optional[float] = None,
        boll_mid: Optional[float] = None,
        boll_dn: Optional[float] = None,
        id: int = 0,
    ) -> Kline:
        """工厂方法：创建K线聚合根"""
        kline = cls(
            id=id,
            symbol=StockCode(symbol),
            trade_date=TradeDate(trade_date),
            name=name,
            open=open,
            high=high,
            low=low,
            close=close,
            volume=volume,
            amount=amount,
            change_pct=change_pct,
            ma5=ma5,
            ma10=ma10,
            ma20=ma20,
            ma60=ma60,
            ema12=ema12,
            ema26=ema26,
            macd_dif=macd_dif,
            macd_dea=macd_dea,
            macd_bar=macd_bar,
            rsi6=rsi6,
            rsi12=rsi12,
            rsi24=rsi24,
            kdj_k=kdj_k,
            kdj_d=kdj_d,
            kdj_j=kdj_j,
            boll_up=boll_up,
            boll_mid=boll_mid,
            boll_dn=boll_dn,
        )
        kline.validate()
        return kline