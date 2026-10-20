"""采集 trigger 响应 DTO（POST 执行结果）

字段对齐 application/service/base.py::CollectResult。

⚠️ 重要：所有 trigger 路由必须用 ApiResponse[CollectResponse] 作为 response_model，
   这样 FastAPI 才会保留 R.ok() 的 {code, message, data} 包装结构，前端 unwrap() 才能
   正确取到 d.data。如果只用 CollectResponse，FastAPI 会把 R.ok() 的包装字段过滤掉，
   导致前端拿不到 d.data。
"""
from __future__ import annotations

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应包装（与 shared.interface._response.R.ok() 一致）

    字段：
      code    业务状态码（200=成功，其它=失败）
      message 提示信息
      data    业务数据
    """
    code: int = 200
    message: str = "success"
    data: T


class CollectResponse(BaseModel):
    """POST /api/collect/{facet}/{service_name} 响应的 data 部分

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


__all__ = ["ApiResponse", "CollectResponse"]
