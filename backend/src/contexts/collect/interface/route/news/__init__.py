"""news routes — 新闻 1 个 service 对应 1 个 route

URL 风格：POST /collect/news/news
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from shared.interface import _response as R
from contexts.collect.infrastructure.di.collect_service import get_news_service

router = APIRouter(prefix="/collect/news", tags=["采集-新闻"])


class CollectBody(BaseModel):
    """采集请求体

    新格式：{"mode": "full" | "condition", "params": {...}}
    旧格式：{"params": {...}}    兼容：mode 默认为 condition
    """
    mode: str = "condition"
    params: dict = Field(default_factory=dict)


@router.post("/news", summary="新闻快讯采集")
async def news_trigger(body: CollectBody, svc=Depends(get_news_service)):
    merged = {**body.params, "mode": body.mode}
    return R.ok((await svc.collect(merged)).to_dict())


__all__ = ["router"]
