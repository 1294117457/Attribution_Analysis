"""log — 采集日志查询路由

提供：
    GET /collect/logs/{service_name}            日志列表
    GET /collect/logs/{service_name}/{log_id}   单条日志详情

设计说明：
    - Route 层不持有 session
    - 通过 Depends(get_collect_log_service) 注入
    - 实时进度由 CollectLogService 内部合并（DB + Redis）

Phase 2 重构（2026-10-19）：
    - 从 manage/ 迁入 route/log.py
    - 日志子系统独立闭环
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from shared.interface import _response as R
from contexts.collect.application.service.manage import CollectLogService
from contexts.collect.infrastructure.di.log_service import get_collect_log_service

router = APIRouter(prefix="/collect/logs", tags=["采集-日志查询"])


@router.get(
    "/{service_name}",
    summary="查询某 service 的最近采集日志",
)
async def list_logs(
    service_name: str,
    limit: int = 10,
    log_service: CollectLogService = Depends(get_collect_log_service),
) -> dict[str, Any]:
    """查询最近 limit 条日志（DB + Redis 实时进度合并）"""
    items = await log_service.list_logs(service_name=service_name, limit=limit)
    return R.ok({"items": items})


@router.get(
    "/{service_name}/{log_id}",
    summary="查询单条采集日志详情",
)
async def get_log(
    service_name: str,
    log_id: str,
    log_service: CollectLogService = Depends(get_collect_log_service),
) -> dict[str, Any]:
    """查询单条日志（DB + Redis 实时进度合并）"""
    log = await log_service.get_log(log_id=log_id, service_name=service_name)
    if log is None:
        raise HTTPException(status_code=404, detail=f"日志 {log_id!r} 不存在")
    return R.ok(log)


__all__ = ["router"]
