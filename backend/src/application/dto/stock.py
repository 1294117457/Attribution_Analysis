"""股票应用层 DTO"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


# ── 请求 DTO ──────────────────────────────────────────────

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


class StockQueryRequest(BaseModel):
    """股票列表查询请求（支持分页/搜索/多维筛选）"""

    q: Optional[str] = Field(None, description="代码 / 名称模糊搜索")
    industry: Optional[str] = Field(None, description="行业")
    market: Optional[str] = Field(None, description="市场类型")
    exchange: Optional[str] = Field(None, description="交易所 SSE/SZSE/BSE")
    is_hs: Optional[str] = Field(None, description="沪深港通 N/H/S")
    list_status: Optional[str] = Field("L", description="上市状态 L/D/P/全部")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=500, description="每页条数")


# ── 响应 DTO ──────────────────────────────────────────────

class StockItemResponse(BaseModel):
    """股票详情响应（单只）"""
    symbol: str
    name: Optional[str] = None
    industry: Optional[str] = None
    market: Optional[str] = None
    list_date: Optional[date] = None
    total_shares: Optional[int] = None


class StockListItemResponse(BaseModel):
    """股票列表项（含 K 线统计）"""
    symbol: str
    name: Optional[str] = None
    industry: Optional[str] = None
    market: Optional[str] = None
    record_count: int = 0
    kline_start: Optional[date] = None
    kline_end: Optional[date] = None


class StockQueryItemResponse(BaseModel):
    """股票查询项（富字段 + K线统计 + 最新估值，StockInfoList.vue 主列表用）"""
    symbol: str
    ts_code: Optional[str] = None
    name: Optional[str] = None
    area: Optional[str] = None
    industry: Optional[str] = None
    market: Optional[str] = None
    exchange: Optional[str] = None
    list_date: Optional[str] = None
    list_status: Optional[str] = None
    is_hs: Optional[str] = None
    act_name: Optional[str] = None
    act_ent_type: Optional[str] = None
    record_count: int = 0
    kline_start: Optional[date] = None
    kline_end: Optional[date] = None
    latest_close: Optional[float] = None
    total_mv: Optional[float] = None
    pe_ttm: Optional[float] = None


class StockListResponse(BaseModel):
    """股票列表响应（含分页，DataCollect/StockManage 用）"""
    total: int
    page: int = 1
    page_size: int = 20
    items: list[StockListItemResponse]


class StockQueryResponse(BaseModel):
    """股票查询响应（StockPanel.vue 用，富字段）"""
    total: int
    page: int = 1
    page_size: int = 20
    items: list[StockQueryItemResponse]


class StockDeleteResponse(BaseModel):
    """删除股票响应"""
    symbol: str
    deleted_count: int
    message: str


class StockMetaResponse(BaseModel):
    """股票元数据（枚举值）"""
    industries: list[str] = Field(default_factory=list)
    markets: list[str] = Field(default_factory=list)
    exchanges: list[str] = Field(default_factory=list)


class SyncStockResponse(BaseModel):
    """同步股票响应"""
    synced_count: int
    inserted: int = 0
    updated: int = 0
    message: str = ""
