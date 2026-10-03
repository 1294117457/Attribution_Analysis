"""概念大盘 — 请求 DTO（01 概念大盘页 v2 纯增量方案）

配套设计文档：
  docs/dev/step3/02发散探索/01-概念大盘页.md §3.2

本文件为**纯新增**，不动任何已有 DTO。
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

# 概念类型筛选（与 route/dto/response/concept.py 的 CONCEPT_TYPE_ORDER 对齐）
ConceptTypeFilter = Literal[
    "all", "industry", "theme", "style", "region", "event", "other"
]


class ConceptBoardQueryRequest(BaseModel):
    """概念大盘查询请求（涨/跌 Top + 全量分页复用）

    典型用法：
    - 「涨 Top 20」：sort_by=pct_change&order=desc&page_size=20
    - 「跌 Top 20」：sort_by=pct_change&order=asc&page_size=20
    - 「全部」：type_filter=all&page_size=500
    """
    type_filter: ConceptTypeFilter = Field(
        "all", description="概念类型筛选（all=全部）"
    )
    sort_by: Literal["pct_change", "stock_count", "name"] = Field(
        "pct_change", description="排序键"
    )
    order: Literal["asc", "desc"] = Field("desc", description="升降序")
    page: int = Field(1, ge=1, description="页码（全量分页模式时有效）")
    page_size: int = Field(50, ge=1, le=500, description="每页条数")


class ConceptMembersQueryRequest(BaseModel):
    """概念成分股查询请求"""
    concept_id: int = Field(..., description="概念 id")
    sort_by: Literal["pct_change", "latest_close", "total_mv", "name"] = Field(
        "pct_change", description="排序键"
    )
    order: Literal["asc", "desc"] = Field("desc", description="升降序")
    with_pools: bool = Field(True, description="是否附带所属操作池（避免 N+1）")
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=200)


__all__ = [
    "ConceptTypeFilter",
    "ConceptBoardQueryRequest",
    "ConceptMembersQueryRequest",
]
