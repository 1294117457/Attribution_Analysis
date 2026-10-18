"""概念路由 — 行情端点 /api/v1/concepts/*

包含：
- GET /quotes         批量概念实时行情（实时接口 concept_minute，15 秒缓存）
- GET /{index_code}/minute  单概念当日分时（实时接口 concept_minute）
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from contexts.collect.application.service.base import (
    InvalidParams,
    RateLimited,
    SourceUnavailable,
)
from contexts.concept.application.service.concept_service import ConceptService
from contexts.concept.infrastructure.di import get_concept_service
from shared.interface import _response as R

router = APIRouter(prefix="/concepts", tags=["概念"])

MAX_QUOTE_CODES = 100


@router.get(
    "/quotes",
    response_model=None,
    summary="批量概念实时行情（实时接口 concept_minute，15 秒缓存）",
)
async def get_concept_quotes(
    codes: str = Query(..., description="index_code 列表，逗号分隔，最多 100 个"),
    app: ConceptService = Depends(get_concept_service),
):
    """返回 {index_code: quote}；取不到的概念不出现在结果中。"""
    code_list = list(dict.fromkeys(c.strip() for c in codes.split(",") if c.strip()))
    if len(code_list) > MAX_QUOTE_CODES:
        return R.err(f"codes 最多 {MAX_QUOTE_CODES} 个", 400)
    return R.ok(await app.get_quotes(code_list))


@router.get(
    "/{index_code}/minute",
    response_model=None,
    summary="单概念当日分时（实时接口 concept_minute）",
)
async def get_concept_minute(
    index_code: str,
    app: ConceptService = Depends(get_concept_service),
):
    try:
        res = await app.get_minute(index_code)
    except InvalidParams as e:
        return R.err(str(e), 400)
    except (RateLimited, SourceUnavailable) as e:
        return R.err(str(e), 502)
    return R.ok({
        **(res.data or {}), "stale": res.stale,
        "cached": res.cached, "fetched_at": res.fetched_at,
    })
