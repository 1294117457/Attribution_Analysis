"""采集 trigger 响应 DTO（POST 执行结果）

字段对齐 application/service/base.py::CollectResult。
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CollectResponse(BaseModel):
    """POST /api/collect/{facet}/{service_name} 响应

    两种模式：
    - 同步：total/success/fail/skip/saved 有值（≤ legacy，已废弃）
    - 异步派发：log_id + status（"pending"/"running"/"failed"）
    """
    # 同步执行结果（旧，保留兼容）
    total: int = 0
    success: int = 0
    fail: int = 0
    skip: int = 0
    saved: int = 0
    message: str = ""
    # 异步派发结果（当前主路径）
    log_id: str | None = None
    status: Literal["pending", "running", "success", "failed", "partial_fail"] | None = None


__all__ = ["CollectResponse"]
