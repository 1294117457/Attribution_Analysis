"""sentiment routes — 情绪面 1 个 service 对应 1 个 route

Phase3：内联 CollectBody → DTO CollectRequest / CollectResponse
该 service 为占位，sentiment 不在 _HIDDEN_SERVICES 之外暴露。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from shared.interface import _response as R
from contexts.collect.interface.dto.request.collect import CollectRequest
from contexts.collect.interface.dto.response.collect import CollectResponse
from contexts.collect.infrastructure.di.collect_service import get_sentiment_service

router = APIRouter(prefix="/collect/sentiment", tags=["采集-情绪面"])


async def _run(svc, body: CollectRequest) -> CollectResponse:
    result = await svc.collect(body.params)
    return CollectResponse(
        total=result.total, success=result.success, fail=result.fail,
        skip=result.skip, saved=result.saved, message=result.message,
    )


@router.post("/sentiment", response_model=CollectResponse, summary="情绪面（占位）")
async def sentiment_trigger(body: CollectRequest, svc=Depends(get_sentiment_service)):
    return R.ok((await _run(svc, body)).model_dump())


__all__ = ["router"]
