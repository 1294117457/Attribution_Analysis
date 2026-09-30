"""概念路由（只读查询；采集走 /collect/tasks 的 concept* 任务）

配套设计文档：
  docs/dev/06gainian/03-application-and-route-design.md §3.1
  docs/dev/step2/02datamanage/04-概念数据adata同源改造方案.md §5.5
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from application.service.concept_app_service import ConceptAppService
from application.service.realtime_app_service import RealtimeQueryError, get_realtime_app_service
from route.dto.response.concept import ConceptQueryRequest
from domain.entitys.concept.entity import ConceptNotFoundError
from application.port.collector_port import ConceptFetcher
from application.port.registry import get_registry
from infrastructure.persistence.connection import get_db
from infrastructure.persistence.repositories.concept_repository import ConceptRepoImpl
from route.api import _response as R

router = APIRouter(prefix="/concepts", tags=["概念"])

MAX_QUOTE_CODES = 100


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
    q: Optional[str] = Query(None, description="模糊搜索概念名称，或精确匹配 index_code"),
    is_active: Optional[bool] = Query(None, description="是否有效"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    app: ConceptAppService = Depends(get_concept_app_service),
):
    """分页列出所有概念（支持 q / is_active 筛选，按成分股数量降序）"""
    req = ConceptQueryRequest(
        q=q,
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
    "/live-by-symbol/{symbol}",
    response_model=None,
    summary="单股票所属概念（同花顺实时反查，带入选理由）",
)
async def get_live_concepts_by_symbol(
    symbol: str,
    app: ConceptAppService = Depends(get_concept_app_service),
):
    """单股票所属概念列表（adata 实时拉取同花顺 F10，**带入选理由 reason**）

    与 /by-symbol/{symbol} 的区别：
    - /by-symbol：从库读，由概念成分股 / 入选理由采集任务维护
    - /live-by-symbol：实时拉取，每次返回最新；包含 `reason` 字段

    适用场景：
    - 详情抽屉「概念」Tab 用户点"实时刷新"按钮
    - 概念搜索联想（输入股票代码，秒级返回概念）

    注意：
    - 单只股票约 0.5s；批量请求请走 /by-symbol 走 DB
    - 当前实现依赖 adata 网络；网络故障时返回 []
    """
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
    app: ConceptAppService = Depends(get_concept_app_service),
):
    """单股票所属概念 Tab 内容

    merge_live=false（默认）：
        返回 ConceptTabContentVO，仅含库中数据。

    merge_live=true：
        调 ConceptAppService.get_tab_content_with_live，
        返回 ConceptTabContentVO（is_merged=true，含 reason / is_realtime 字段），
        适用于「概念」Tab 的"实时刷新"按钮。
    """
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
    codes: str = Query(..., description="index_code 列表，逗号分隔，最多 100 个，如 885525,885642"),
    app: ConceptAppService = Depends(get_concept_app_service),
):
    """返回 {index_code: quote}；取不到的概念不出现在结果中。quote.stale=true 表示数据源失败、显示最近收盘"""
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
        res = await get_realtime_app_service().query("concept_minute", {"index_code": index_code})
    except ValueError as e:
        return R.err(str(e), 400)
    except RealtimeQueryError as e:
        return R.err(str(e), 502)
    return R.ok({**(res.data or {}), "stale": res.stale, "cached": res.cached, "fetched_at": res.fetched_at})


@router.get(
    "/{name}",
    response_model=None,
    summary="单概念详情",
)
async def get_concept_detail(
    name: str,
    app: ConceptAppService = Depends(get_concept_app_service),
):
    """单概念详情（含成分股与入选理由，读库）"""
    try:
        result = await app.get_concept_detail(name=name)
        return R.ok(result.model_dump())
    except ConceptNotFoundError as e:
        raise HTTPException(404, e.message)


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
        "last_synced_at": (
            last_synced_at.isoformat() if last_synced_at else None
        ),
        "active_concepts": total,
    })


# ═══════════════════════════════════════════════════════════════════════════════
#  行情端点
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/{name}/index-th",
    response_model=None,
    summary="取概念指数日 K（按日期范围）",
)
async def get_concept_index_th(
    name: str,
    start_date: Optional[date] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[date] = Query(None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(500, ge=1, le=2000, description="最大行数"),
    db: AsyncSession = Depends(get_db),
):
    """取指定概念指数日 K（09concept 新增，P1 功能）

    按 trade_date DESC 排序。
    """
    repo = ConceptRepoImpl(db)
    rows = await repo.list_index_th(
        concept_name=name,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return R.ok(rows)
