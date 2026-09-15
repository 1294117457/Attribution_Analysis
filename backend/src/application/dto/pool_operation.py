"""池操作相关 DTO"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class PoolKlineCollectRequest(BaseModel):
    """采集 K 线请求"""
    pool_id: int = Field(..., description="池 ID")
    operation_type: Literal["kline_collect"] = "kline_collect"
    days: int = Field(365, ge=1, le=3650, description="回溯天数")
    source: Optional[str] = Field(None, description="数据源 tushare/akshare")


class PoolOperationListRequest(BaseModel):
    pool_id: int
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class PoolOperationProgressVO(BaseModel):
    done: int = 0
    total: int = 0
    failed: int = 0

    @property
    def percent(self) -> int:
        if self.total == 0:
            return 0
        return int(self.done / self.total * 100)


class PoolOperationDetailItemVO(BaseModel):
    symbol: str
    status: str
    count: Optional[int] = None
    message: Optional[str] = None


class PoolOperationVO(BaseModel):
    id: int
    pool_id: Optional[int] = None
    operation_type: str
    status: str
    params: dict = Field(default_factory=dict)
    result_summary: Optional[dict] = None
    progress: PoolOperationProgressVO
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PoolOperationListResponse(BaseModel):
    pool_id: int
    total: int
    items: list[PoolOperationVO]


class PoolOperationCreateResponse(BaseModel):
    operation_id: int
    pool_id: int
    operation_type: str
    status: str
    total: int
    message: str = "操作已派发"


class PoolOperationDetailResponse(BaseModel):
    operation: PoolOperationVO
    details: list[PoolOperationDetailItemVO]
