"""股票归因分析 DTO - /stocks/{symbol}/analysis 响应结构"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
#  子结构
# ═══════════════════════════════════════════════════════════════


class StockInfoVO(BaseModel):
    """股票基本信息"""
    symbol: str
    name: str
    industry: Optional[str] = None
    market: Optional[str] = None


class TechnicalSummaryVO(BaseModel):
    """技术形态摘要（后端聚合好, AI/前端直接用）"""
    latest_close: float
    pct_change_1d: float
    pct_change_30d: float

    ma_alignment: str                       # bullish / bearish / neutral
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None
    ma5_above_ma20: bool
    golden_cross_recent: bool

    macd_status: str                        # golden_cross / death_cross / above_zero / below_zero / neutral
    macd_dif: float
    macd_dea: float
    macd_bar: float

    rsi6: float
    rsi_status: str                         # overbought / oversold / neutral

    kdj_k: float
    kdj_d: float
    kdj_j: float
    kdj_status: str

    boll_up: Optional[float] = None
    boll_mid: Optional[float] = None
    boll_dn: Optional[float] = None
    boll_position: str                      # above_upper / below_lower / upper_half / lower_half / middle

    signals: list[str] = Field(default_factory=list)


class KlineWithIndicatorVO(BaseModel):
    """单日 K 线 + 指标"""
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: Optional[float] = None
    change_pct: Optional[float] = None

    # 指标（来自 daily_klines 展宽列）
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


class PoolMembershipVO(BaseModel):
    """所在池"""
    pool_id: int
    pool_name: str
    joined_at: Optional[str] = None


# ═══════════════════════════════════════════════════════════════
#  顶层响应
# ═══════════════════════════════════════════════════════════════


class StockAnalysisResponse(BaseModel):
    """完整分析响应 - /stocks/{symbol}/analysis"""
    stock: StockInfoVO
    summary: TechnicalSummaryVO
    klines: list[KlineWithIndicatorVO]
    pools: list[PoolMembershipVO] = Field(default_factory=list)