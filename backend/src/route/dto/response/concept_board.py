"""概念大盘 — 响应 DTO（01 概念大盘页 v2 纯增量方案）

配套设计文档：
  docs/dev/step3/02发散探索/01-概念大盘页.md §3.3

字段对齐：
- ConceptBoardItemVO：与 ConceptItemVO 对齐 + 实时行情字段（price/pct_change/color/stale）
- ConceptMemberItemVO：与 StockPanelItemVO 字段基本对齐 + 池信息

v2 矫正：CONCEPT_TYPE_LABELS 直接 import 自已有 route/dto/response/concept.py，
不重复定义。
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from application.port.page import Page
from route.dto.response.concept import CONCEPT_TYPE_LABELS
from route.dto.response.pool import PoolMembershipVO

# v2：与现有 CONCEPT_TYPE_LABELS 等价的别名，便于概念大盘语义独立
CONCEPT_BOARD_TYPE_LABELS = CONCEPT_TYPE_LABELS


class ConceptBoardItemVO(BaseModel):
    """概念大盘行 VO（卡片/榜单共用）

    来源：concepts + concept_minute 实时接口（带 fallback）。
    字段：与 ConceptItemVO 对齐 + 实时涨幅 + 类型标签。
    """
    concept_id: int
    index_code: str
    name: str
    source: str
    concept_type: str
    concept_type_label: str
    stock_count: int
    description: Optional[str] = None

    # ── 实时行情（来自 RealtimeQueryFramework.query("concept_minute")）──
    price: Optional[float] = None
    prev_close: Optional[float] = None
    change: Optional[float] = None
    pct_change: Optional[float] = None
    color: str = "flat"
    trade_time: Optional[str] = None
    captured_at: Optional[str] = None
    stale: bool = False

    model_config = {"from_attributes": True}


class ConceptBoardListVO(BaseModel):
    """概念大盘分页响应（手写 Page-like 形状，避免与 Page[T] 序列化差异）

    字段顺序与前端 PaginatedResponse<T> 1:1 对齐：
    items / total / page / page_size / pages
    """
    items: List[ConceptBoardItemVO] = Field(default_factory=list)
    total: int = Field(0, ge=0)
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1)
    pages: int = Field(0, ge=0)


class ConceptMemberItemVO(BaseModel):
    """概念成分股 VO（与 StockPanelItemVO 字段基本对齐，去掉 concept 列）"""
    symbol: str
    name: Optional[str] = None
    industry: Optional[str] = None
    market: Optional[str] = None

    # ── 来自 fin_daily_basics（最新一天）──
    latest_close: Optional[float] = None
    total_mv: Optional[float] = None
    pe_ttm: Optional[float] = None

    # ── 实时（来自 RealtimeQueryFramework.query("stock_minute_kline")）──
    # 注：单股实时需每只调一次，开销大；本期只对前 50 只按需触发
    pct_change: Optional[float] = None
    color: str = "flat"

    # ── 池信息 ──
    pools: List[PoolMembershipVO] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ConceptMemberListVO(BaseModel):
    """概念成分股分页响应"""
    items: List[ConceptMemberItemVO] = Field(default_factory=list)
    total: int = Field(0, ge=0)
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1)
    pages: int = Field(0, ge=0)


# ═══════════════════════════════════════════════════════════════════════
#  概念 K 线（concept_index_ths + 实时）
# ═══════════════════════════════════════════════════════════════════════


class ConceptKlineBarVO(BaseModel):
    """概念指数单日 K 线"""
    date: str                              # "2026-10-02"
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: Optional[float] = None
    change_pct: Optional[float] = None
    color: str = "flat"                    # up / down / flat

    model_config = {"from_attributes": True}


class ConceptKlineMetaVO(BaseModel):
    """概念 meta（用于 K 线头部展示）"""
    concept_id: Optional[int] = None
    index_code: str
    name: str
    concept_type: Optional[str] = None
    concept_type_label: Optional[str] = None
    stock_count: Optional[int] = None
    description: Optional[str] = None
    source: Optional[str] = None


class ConceptKlineRangeVO(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None
    bars_count: int = 0


class ConceptKlineResponseVO(BaseModel):
    """概念 K 线 + 实时 响应"""
    kline: List[ConceptKlineBarVO] = Field(default_factory=list)
    realtime: Optional[dict] = None
    meta: Optional[ConceptKlineMetaVO] = None
    data_range: ConceptKlineRangeVO = Field(default_factory=ConceptKlineRangeVO)


__all__ = [
    "CONCEPT_BOARD_TYPE_LABELS",
    "ConceptBoardItemVO",
    "ConceptBoardListVO",
    "ConceptMemberItemVO",
    "ConceptMemberListVO",
    "ConceptKlineBarVO",
    "ConceptKlineMetaVO",
    "ConceptKlineRangeVO",
    "ConceptKlineResponseVO",
]
