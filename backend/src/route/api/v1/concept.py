"""概念路由

业务模块：concepts（共享查询 + 大盘）
- 共享概念查询走 ConceptService（被 stock-info / market 复用）
- 概念大盘 + K 线走 ConceptBoardService

采集相关走 /collect/tasks 的 concept* 任务。
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from application.service import ConceptBoardService, ConceptService
from infrastructure.adapter.realtime import RealtimeQueryError, get_realtime_query_framework
from infrastructure.config.di import (
    get_concept_board_service,
    get_concept_service,
    get_db,
)
from infrastructure.persistence.repositories.concept_repository import ConceptRepoImpl
from route.api import _response as R
from route.dto.request.concept_board import (
    ConceptBoardQueryRequest,
    ConceptMembersQueryRequest,
)
from route.dto.response.concept import ConceptQueryRequest

router = APIRouter(prefix="/concepts", tags=["概念"])

MAX_QUOTE_CODES = 100


# ═══════════════════════════════════════════════════════════════════════════════
#  概念大盘（业务模块：concept-board/）· 路由前部以优先于 /{name} 通配符匹配
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/concept-board",
    response_model=None,
    summary="概念大盘（涨/跌 Top + 全量分页）",
)
async def get_concept_board(
    type_filter: str = Query("all", description="概念类型筛选（all/industry/theme/...）"),
    sort_by: str = Query("pct_change", description="排序键 pct_change/stock_count/name"),
    order: str = Query("desc", description="排序方向 asc/desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    app: ConceptBoardService = Depends(get_concept_board_service),
):
    """概念大盘：返回分页概念 + 实时涨幅。"""
    req = ConceptBoardQueryRequest(
        type_filter=type_filter, sort_by=sort_by, order=order,
        page=page, page_size=page_size,
    )
    result = await app.query_board(req)
    return R.ok(result)


@router.get(
    "/concept-board/members",
    response_model=None,
    summary="概念成分股列表（带最新价/涨跌幅/换手 + 池）",
)
async def get_concept_board_members(
    concept_id: int = Query(..., description="概念 id"),
    sort_by: str = Query("pct_change"),
    order: str = Query("desc"),
    with_pools: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    app: ConceptBoardService = Depends(get_concept_board_service),
):
    """概念成分股：join stock_infos + fin_daily_basics 最新一行。"""
    req = ConceptMembersQueryRequest(
        concept_id=concept_id, sort_by=sort_by, order=order,
        with_pools=with_pools, page=page, page_size=page_size,
    )
    result = await app.query_board_members(req)
    return R.ok(result)


@router.get(
    "/{index_code}/kline",
    response_model=None,
    summary="概念指数日 K + 实时快照",
)
async def get_concept_kline(
    index_code: str,
    days: int = Query(250, ge=10, le=1500, description="最多取多少根 K 线"),
    start_date: Optional[date] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[date] = Query(None, description="结束日期 YYYY-MM-DD"),
    app: ConceptBoardService = Depends(get_concept_board_service),
):
    """概念指数日 K（concept_index_ths）+ 实时快照

    实时不可用时降级为最近一日收盘。
    """
    result = await app.get_kline(
        index_code=index_code,
        start_date=start_date, end_date=end_date, days=days,
    )
    return R.ok(result)


# ═══════════════════════════════════════════════════════════════════════════════
#  共享概念查询（业务模块：共享层）
# ═══════════════════════════════════════════════════════════════════════════════


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
    live_vos = app.fetch_concepts_by_stock(symbol)
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
async def get_concept_minute(index_code: str):
    try:
        res = await get_realtime_query_framework().query(
            "concept_minute", {"index_code": index_code},
        )
    except ValueError as e:
        return R.err(str(e), 400)
    except RealtimeQueryError as e:
        return R.err(str(e), 502)
    return R.ok({
        **(res.data or {}), "stale": res.stale,
        "cached": res.cached, "fetched_at": res.fetched_at,
    })


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
    db: AsyncSession = Depends(get_db),
):
    """查询最近同步状态（成分股最近同步时间 + 活跃概念数）"""
    repo = ConceptRepoImpl(db)
    last_synced_at = await repo.get_last_synced_at()
    total = await repo.count_concepts(is_active=True)
    return R.ok({
        "last_synced_at": last_synced_at.isoformat() if last_synced_at else None,
        "active_concepts": total,
    })


# ═══════════════════════════════════════════════════════════════════════════════
#  行情端点
# ═══════════════════════════════════════════════════════════════════════════════


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
    db: AsyncSession = Depends(get_db),
):
    """取指定概念指数日 K（兼容旧接口）"""
    repo = ConceptRepoImpl(db)
    rows = await repo.list_index_th(
        concept_name=name,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return R.ok(rows)
