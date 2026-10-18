"""sentiment routes — 情绪面 1 个 service 对应 1 个 route（占位）

URL 风格：POST /collect/sentiment/sentiment
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from shared.interface import _response as R
from contexts.collect.infrastructure.di.collect_service import get_sentiment_service

router = APIRouter(prefix="/collect/sentiment", tags=["采集-情绪面"])


class CollectBody(BaseModel):
    """采集请求体

    新格式：{"mode": "full" | "condition", "params": {...}}
    旧格式：{"params": {...}}    兼容：mode 默认为 condition
    """
    mode: str = "condition"
    params: dict = Field(default_factory=dict)


@router.post("/sentiment", summary="情绪面（占位）")
async def sentiment_trigger(body: CollectBody, svc=Depends(get_sentiment_service)):
    merged = {**body.params, "mode": body.mode}
    return R.ok((await svc.collect(merged)).to_dict())


__all__ = ["router"]
