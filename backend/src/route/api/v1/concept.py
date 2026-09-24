"""概念路由

配套设计文档：
  docs/dev/06gainian/03-application-and-route-design.md §3.1
"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from application.concept_service import ConceptAppService
from application.dto.concept import (
    ConceptDetailVO,
    ConceptItemVO,
    ConceptQueryRequest,
    ConceptSyncRequest,
    ConceptSyncResultVO,
    ConceptTabContentVO,
)
from application.dto.page import Page
from domain.concept.exceptions import ConceptNotFoundError
from infrastructure.collectors.protocols import ConceptFetcher
from infrastructure.collectors.registry import get_registry
from infrastructure.database.connection import get_db
from infrastructure.repositories.concept_repository import ConceptRepoImpl
from route.schemas import response as R

router = APIRouter(prefix="/concepts", tags=["概念"])


# ── 依赖注入 ────────────────────────────────────────


def get_concept_app_service(
    db: AsyncSession = Depends(get_db),
) -> ConceptAppService:
    """构造 ConceptAppService 实例"""
    registry = get_registry()
    if not registry.has(ConceptFetcher):
        raise HTTPException(503, "概念采集器未注册")
    fetcher = registry.get(ConceptFetcher)
    repo = ConceptRepoImpl(db)
    return ConceptAppService(repo=repo, fetcher=fetcher)


# ── 路由定义 ────────────────────────────────────────


@router.get(
    "/",
    response_model=None,
    summary="分页列出所有概念",
)
async def list_concepts(
    q: Optional[str] = Query(None, description="模糊搜索概念名称"),
    source: Optional[str] = Query(None, description="数据源：em / ths"),
    is_active: Optional[bool] = Query(None, description="是否有效"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    app: ConceptAppService = Depends(get_concept_app_service),
):
    """分页列出所有概念（支持 q / source / is_active 筛选）"""
    req = ConceptQueryRequest(
        q=q,
        source=source,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )
    result = await app.query_concepts(req)
    return R.ok(result.model_dump())


@router.get(
    "/by-symbol/{symbol}",
    response_model=None,
    summary="单股票所属概念（简略版）",
)
async def get_concepts_by_symbol(
    symbol: str,
    app: ConceptAppService = Depends(get_concept_app_service),
):
    """单股票所属概念列表（轻量版，仅 concept_id / name / source）

    用于详情抽屉「概念」Tab 的快速打开（避免首屏就拉全量）。
    前端拿到后可直接渲染概念 Tag；如果用户切到「概念」Tab，
    再调下方的 /tab-by-symbol/{symbol} 拿全量分组数据。
    """
    vos = await app.list_for_symbol(symbol)
    return R.ok([{"concept_id": v.concept_id, "name": v.name, "source": v.source} for v in vos])


@router.get(
    "/tab-by-symbol/{symbol}",
    response_model=None,
    summary="单股票所属概念 Tab 内容（按类型分组）",
)
async def get_concept_tab_for_symbol(
    symbol: str,
    stock_name: Optional[str] = Query(None, description="股票名称（仅用于头部展示）"),
    app: ConceptAppService = Depends(get_concept_app_service),
):
    """单股票所属概念 Tab 内容（按 concept_type 分组，含 description）

    抽屉「概念」Tab 切换时调用，返回 ConceptTabContentVO，
    前端 ConceptTab.vue 直接消费，无需再做分组 / 排序。
    """
    result = await app.get_tab_content_for_symbol(symbol, stock_name=stock_name)
    return R.ok(result.model_dump())


@router.get(
    "/{name}",
    response_model=None,
    summary="单概念详情",
)
async def get_concept_detail(
    name: str,
    source: str = Query("em", description="数据源：em / ths"),
    app: ConceptAppService = Depends(get_concept_app_service),
):
    """单概念详情（含成分股）"""
    try:
        result = await app.get_concept_detail(name=name, source=source)
        return R.ok(result.model_dump())
    except ConceptNotFoundError as e:
        raise HTTPException(404, e.message)


@router.post(
    "/sync",
    response_model=None,
    summary="触发概念全量/增量同步",
)
async def sync_concepts(
    source: str = Query("em", description="数据源：em / ths"),
    app: ConceptAppService = Depends(get_concept_app_service),
):
    """触发概念全量/增量同步（后台任务）"""
    req = ConceptSyncRequest(source=source)
    result = await app.sync_concepts(req)
    return R.ok(result.model_dump())


@router.get(
    "/sync/status",
    summary="查询最近同步状态",
)
async def get_sync_status(
    db: AsyncSession = Depends(get_db),
):
    """查询最近同步状态（取 last_synced_at 最大值）"""
    repo = ConceptRepoImpl(db)
    last_synced_at = await repo.get_last_synced_at(source="em")
    total = await repo.count_concepts(source="em", is_active=True)
    return R.ok({
        "last_synced_at": (
            last_synced_at.isoformat() if last_synced_at else None
        ),
        "active_concepts": total,
    })
