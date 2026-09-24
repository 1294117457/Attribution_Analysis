"""StockPanel 列表 DTO

StockPanel 是"列表 + 4 表快照"组合视图的对外 DTO，
所有字段均来自 stock_infos / tech_kline_dailys / fin_daily_basics / fin_reports
四张表的 JOIN / 子查询结果。

字段命名 / 类型与后端 ORM 保持 snake_case，
与前端 PaginatedResponse<StockInfo> 1:1 对齐。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from application.dto.page import Page
from application.dto.pool import PoolMembershipVO
from domain.concept.value_objects import ConceptBriefVO


# ═══════════════════════════════════════════════════════════════════════════════
#  请求 DTO
# ═══════════════════════════════════════════════════════════════════════════════


class StockPanelQueryRequest(BaseModel):
    """列表面板查询请求（与 StockPanelComposeRepository.list_paginated 参数对齐）"""
    q: Optional[str] = Field(None, description="代码 / 名称 / 拼音 模糊搜索")
    industry: Optional[str] = Field(None, description="行业")
    market: Optional[str] = Field(None, description="市场类型")
    exchange: Optional[str] = Field(None, description="交易所 SSE/SZSE/BSE")
    is_hs: Optional[str] = Field(None, description="沪深港通 N/H/S")
    list_status: Optional[str] = Field("L", description="上市状态 L/D/P/全部")
    exclude_st: Optional[bool] = Field(None, description="排除 ST / 仅 ST")
    min_total_mv: Optional[float] = Field(None, ge=0, description="最低总市值(万元)")
    with_pools: bool = Field(False, description="是否附带所属操作池（避免 N+1）")
    with_concepts: bool = Field(False, description="是否附带所属概念板块（详情抽屉预热用）")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=500, description="每页条数")


# ═══════════════════════════════════════════════════════════════════════════════
#  响应 DTO
# ═══════════════════════════════════════════════════════════════════════════════


class StockPanelItemVO(BaseModel):
    """列表面板单行 VO（与 StockPanelRow 字段 1:1 + pools 字段）"""

    # ── 来自 stock_infos ────────────────────────────────────
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
    total_shares: Optional[int] = None

    # ── 来自 tech_kline_dailys（聚合）────────────────────────
    record_count: int = 0
    kline_start: Optional[date] = None
    kline_end: Optional[date] = None

    # ── 来自 fin_daily_basics（最新一行）─────────────────────
    latest_close: Optional[float] = None
    total_mv: Optional[float] = None
    pe_ttm: Optional[float] = None

    # ── 来自 fin_reports（最新一期）──────────────────────────
    profit_margin: Optional[float] = None

    # ── 来自 stock_pool_members ⨝ stock_pools ────────────────
    pools: list[PoolMembershipVO] = Field(default_factory=list)

    # ── 来自 stock_concept_members ⨝ concepts（with_concepts=true 时附带）──
    concepts: list[ConceptBriefVO] = Field(default_factory=list)


class StockPanelListVO(Page[StockPanelItemVO]):
    """StockPanel 列表响应（分页 + 4 表快照 + 池信息）

    继承 Page[T] 的 items/total/page/page_size/pages。
    字段命名与前端 PaginatedResponse<StockInfo> 1:1 对齐。
    """
    pass