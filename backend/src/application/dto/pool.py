"""池 CRUD 相关 DTO"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# 请求 DTO
# ═══════════════════════════════════════════════════════════════════════════════


class PoolCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="池名称")
    pool_type: str = Field("custom", description="池类型")
    description: Optional[str] = Field(None, max_length=255)
    color: Optional[str] = Field(None, description="HEX 颜色码，如 #FF5722")
    icon: Optional[str] = Field(None, max_length=32)


class PoolUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    description: Optional[str] = Field(None, max_length=255)
    color: Optional[str] = Field(None)
    icon: Optional[str] = Field(None, max_length=32)
    sort_order: Optional[int] = Field(None, ge=0)


class PoolAddMembersRequest(BaseModel):
    symbols: list[str] = Field(
        ..., min_length=1, max_length=500, description="股票代码列表",
    )
    validate_exists: bool = Field(
        True, description="是否校验股票是否存在",
    )


class PoolRemoveMembersRequest(BaseModel):
    symbols: list[str] = Field(..., min_length=1, max_length=500)


class PoolUpdateMemberMemoRequest(BaseModel):
    symbol: str = Field(..., description="股票代码")
    memo: str = Field("", max_length=255)


# ═══════════════════════════════════════════════════════════════════════════════
# 响应 DTO
# ═══════════════════════════════════════════════════════════════════════════════


class PoolMemberVO(BaseModel):
    symbol: str
    memo: Optional[str] = None
    sort_order: int = 0
    added_at: Optional[datetime] = None
    name: Optional[str] = None
    industry: Optional[str] = None
    market: Optional[str] = None
    exchange: Optional[str] = None
    is_valid: bool = True

    model_config = {"from_attributes": True}


class PoolVO(BaseModel):
    id: int
    name: str
    pool_type: str
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    sort_order: int = 0
    is_default: bool = False
    is_archived: bool = False
    member_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PoolDetailVO(PoolVO):
    members: list[PoolMemberVO] = Field(default_factory=list)


class PoolListResponse(BaseModel):
    total: int
    items: list[PoolVO]


class PoolMemberListResponse(BaseModel):
    pool_id: int
    total: int
    items: list[PoolMemberVO]


class PoolAddMembersResponse(BaseModel):
    pool_id: int
    added: list[str]
    skipped: list[str]
    total_added: int
    total_skipped: int


class PoolPoolsBySymbolResponse(BaseModel):
    symbol: str
    pools: list[PoolVO]
    total: int
