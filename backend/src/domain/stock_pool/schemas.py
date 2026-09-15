"""操作池 - 领域 Schema（VO / BO）"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# 视图对象（API 出参）
# ═══════════════════════════════════════════════════════════════════════════════


class PoolMemberVO(BaseModel):
    """池成员视图对象"""

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


class StockPoolVO(BaseModel):
    """操作池视图对象（API 出参，不含成员）"""

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


class StockPoolDetailVO(StockPoolVO):
    """操作池详情视图对象（包含成员列表）"""

    members: list[PoolMemberVO] = Field(default_factory=list)


class PoolOperationVO(BaseModel):
    """池操作记录视图对象"""

    id: int
    pool_id: Optional[int] = None
    operation_type: str
    status: str
    params: dict = Field(default_factory=dict)
    result_summary: Optional[dict] = None
    progress: dict = Field(default_factory=dict)
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @property
    def progress_text(self) -> str:
        total = self.progress.get("total", 0)
        done = self.progress.get("done", 0)
        if total == 0:
            return "等待中..."
        return f"{done}/{total}"

    @property
    def progress_percent(self) -> int:
        total = self.progress.get("total", 0)
        done = self.progress.get("done", 0)
        if total == 0:
            return 0
        return int(done / total * 100)


# ═══════════════════════════════════════════════════════════════════════════════
# 业务对象（采集层产出 → 领域层）
# ═══════════════════════════════════════════════════════════════════════════════


class StockPoolCreateBO(BaseModel):
    """创建池业务对象"""

    name: str = Field(..., min_length=1, max_length=64)
    pool_type: str = Field(default="custom")
    description: Optional[str] = Field(None, max_length=255)
    color: Optional[str] = Field(None)
    icon: Optional[str] = Field(None, max_length=32)


class StockPoolUpdateBO(BaseModel):
    """更新池业务对象"""

    name: Optional[str] = Field(None, min_length=1, max_length=64)
    description: Optional[str] = Field(None, max_length=255)
    color: Optional[str] = Field(None)
    icon: Optional[str] = Field(None, max_length=32)
    sort_order: Optional[int] = Field(None, ge=0)
