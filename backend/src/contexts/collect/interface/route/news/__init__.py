"""news routes — 新闻 1 个 service 对应 1 个 route

Phase3：内联 CollectBody → DTO CollectRequest / CollectResponse
Phase3 v3（2026-10-19）：news service 走 TaskRunner 派发，返回 {log_id, status}
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from shared.interface import _response as R
from contexts.collect.interface.dto.request.collect import CollectRequest
from contexts.collect.interface.dto.response.collect import ApiResponse, CollectResponse
from contexts.collect.infrastructure.di.collect_service import get_news_service

router = APIRouter(prefix="/collect/news", tags=["采集-新闻"])


async def _run(svc, body: CollectRequest) -> CollectResponse:
    """统一执行：触发后台采集任务"""
    result = await svc.collect(body.params)
    if isinstance(result, dict):
        return CollectResponse(
            log_id=result.get("log_id"),
            status=result.get("status"),
            message=f"采集任务已派发，前端请用 log_id 轮询 /collect/logs/{result.get('log_id')}",
        )
    return CollectResponse(
        total=result.total, success=result.success, fail=result.fail,
        skip=result.skip, saved=result.saved, message=result.message,
    )


@router.post("/news", response_model=ApiResponse[CollectResponse], summary="新闻快讯")
async def news_trigger(body: CollectRequest, svc=Depends(get_news_service)):
    return R.ok((await _run(svc, body)).model_dump())


__all__ = ["router"]