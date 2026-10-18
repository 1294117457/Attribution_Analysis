"""概念路由 — 概念查询（单/多/反查/Tab） /api/v1/concepts/*

包含：
- GET /                     分页列出所有概念
- GET /by-symbol/{symbol}   单股票所属概念（轻量版）
- GET /live-by-symbol/{symbol}   单股票所属概念（同花顺实时反查）
- GET /tab-by-symbol/{symbol}    Tab 内容（按类型分组，支持实时合并）
- GET /{name}               单概念详情
- GET /sync/status          查询最近同步状态
- GET /{name}/index-th      概念指数日 K（按日期范围）
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.concept.application.service.concept_service import ConceptService
from contexts.concept.infrastructure.di import get_concept_service
from contexts.concept.infrastructure.persistence.repositories.concept_repository import (
    ConceptRepoImpl,
)
from shared.infrastructure.di.db_session import get_raw_db
from shared.interface import _response as R

router = APIRouter(prefix="/concepts", tags=["概念"])

from contexts.concept.interface.dto.response.concept import ConceptQueryRequest


@router.get(
    "/",
    response_model=None,
    summary="分页列出所有概念",
)
async def list_concepts(
    q: Optional[str] = Query(None, description="模糊搜索概念名称，或精确匹配 index_code"),
    is_active: Optional[bool] = Query(None, description="是否有效"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    app: ConceptService = Depends(get_concept_service),
):
    """分页列出所有概念（支持 q / is_active 筛选，按成分股数量降序）"""
    req = ConceptQueryRequest(q=q, is_active=is_active, page=page, page_size=page_size)
    items = await app.query_concepts(req)
    return R.ok([item.model_dump() for item in items])


@router.get(
    "/by-symbol/{symbol}",
    response_model=None,
    summary="单股票所属概念（简略版）",
)
async def get_concepts_by_symbol(
    symbol: str,
    app: ConceptService = Depends(get_concept_service),
):
    """单股票所属概念列表（轻量版，仅 concept_id / name / source）"""
    vos = await app.list_for_symbol(symbol)
    return R.ok([{"concept_id": v.concept_id, "name": v.name, "source": v.source} for v in vos])


@router.get(
    "/live-by-symbol/{symbol}",
    response_model=None,
    summary="单股票所属概念（同花顺实时反查，带入选理由）",
)
async def get_live_concepts_by_symbol(
    symbol: str,
    app: ConceptService = Depends(get_concept_service),
):
    """单股票所属概念列表（adata 实时拉取同花顺 F10，**带入选理由 reason**）"""
    live_vos = await app.fetch_concepts_by_stock(symbol)
    return R.ok([v.model_dump() for v in live_vos])


@router.get(
    "/tab-by-symbol/{symbol}",
    response_model=None,
    summary="单股票所属概念 Tab 内容（按类型分组，支持实时合并）",
)
async def get_concept_tab_for_symbol(
    symbol: str,
    stock_name: Optional[str] = Query(None, description="股票名称（仅用于头部展示）"),
    merge_live: bool = Query(
        False,
        description=(
            "是否合并同花顺实时反查数据。默认 false（仅库中数据，已含入选理由 reason）；"
            "true 时返回 is_merged=true 且 sections.concepts 携带 is_realtime 字段"
        ),
    ),
    app: ConceptService = Depends(get_concept_service),
):
    """单股票所属概念 Tab 内容"""
    if merge_live:
        result = await app.get_tab_content_with_live(symbol, stock_name=stock_name)
    else:
        result = await app.get_tab_content_for_symbol(symbol, stock_name=stock_name)
    return R.ok(result.model_dump())


@router.get(
    "/{name}",
    response_model=None,
    summary="单概念详情",
)
async def get_concept_detail(
    name: str,
    app: ConceptService = Depends(get_concept_service),
):
    """单概念详情（含成分股与入选理由，读库）"""
    try:
        result = await app.get_concept_detail(name=name)
        return R.ok(result.model_dump())
    except Exception as e:
        # ConceptNotFoundError 也走这里
        raise HTTPException(404, getattr(e, "message", str(e)))


@router.get(
    "/sync/status",
    summary="查询最近同步状态",
)
async def get_sync_status(
    db: AsyncSession = Depends(get_raw_db),
):
    """查询最近同步状态（成分股最近同步时间 + 活跃概念数）"""
    repo = ConceptRepoImpl(db, None)
    last_synced_at = await repo.get_last_synced_at()
    total = await repo.count_concepts(is_active=True)
    return R.ok({
        "last_synced_at": last_synced_at.isoformat() if last_synced_at else None,
        "active_concepts": total,
    })


@router.get(
    "/{name}/index-th",
    response_model=None,
    summary="取概念指数日 K（按日期范围，按 trade_date DESC）",
)
async def get_concept_index_th(
    name: str,
    start_date: Optional[date] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[date] = Query(None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(500, ge=1, le=2000, description="最大行数"),
    db: AsyncSession = Depends(get_raw_db),
):
    """取指定概念指数日 K（兼容旧接口）"""
    repo = ConceptRepoImpl(db, None)
    rows = await repo.list_index_th(
        concept_name=name,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return R.ok(rows)
