"""股票应用层 DTO

本文件仅保留股票单只 CRUD 所需的 DTO。
面板列表面板（分页 + 4 表快照 + 池信息）的 DTO 已迁移至 application/dto/panel.py。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
#  请求 DTO
# ═══════════════════════════════════════════════════════════════════════════════


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


# ═══════════════════════════════════════════════════════════════════════════════
#  响应 DTO
# ═══════════════════════════════════════════════════════════════════════════════


class StockItemResponse(BaseModel):
    """股票详情响应（单只）"""
    symbol: str
    name: Optional[str] = None
    industry: Optional[str] = None
    market: Optional[str] = None
    list_date: Optional[date] = None
    total_shares: Optional[int] = None


class StockListItemResponse(BaseModel):
    """股票列表项（含 K 线统计，简洁版）

    用于 /stocks/ 简单列表（DataCollect/StockManage 等不需要富字段的场景）。
    面板主列表请使用 application.dto.panel.StockPanelItemVO。
    """
    symbol: str
    name: Optional[str] = None
    industry: Optional[str] = None
    market: Optional[str] = None
    record_count: int = 0
    kline_start: Optional[date] = None
    kline_end: Optional[date] = None


class StockListResponse(BaseModel):
    """股票列表响应（含分页，简单版）

    用于 /stocks/ 简单列表场景。面板主列表请使用 StockPanelListVO。
    """
    total: int
    page: int = 1
    page_size: int = 20
    items: list[StockListItemResponse]


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