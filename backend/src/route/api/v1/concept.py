"""概念路由

配套设计文档：
  docs/dev/06gainian/03-application-and-route-design.md §3.1
  docs/dev/09concept/02-class-design.md §8
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from application.service.concept_app_service import ConceptAppService
from application.dto.concept import (
    ConceptDetailVO,
    ConceptIndexTHVO,
    ConceptItemVO,
    ConceptLiveVO,
    ConceptQueryRequest,
    ConceptSnapshotVO,
    ConceptSyncRequest,
    ConceptSyncResultVO,
    ConceptTabContentVO,
)
from application.dto.page import Page
from domain.concept.exceptions import ConceptNotFoundError
from infrastructure.adapter.adata.fetcher import AdataConceptFetcher
from infrastructure.adapter.akshare.fetcher import AkShareConceptFetcher
from application.port.collector_port import ConceptFetcher
from application.port.registry import get_registry
from infrastructure.persistence.connection import get_db
from infrastructure.persistence.repositories.concept_repository import ConceptRepoImpl
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
    source: Optional[str] = Query(None, description="数据源：ths / em（默认 ths，09concept 改）"),
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
    "/live-by-symbol/{symbol}",
    response_model=None,
    summary="单股票所属概念（adata 实时反查，带入选理由）",
)
async def get_live_concepts_by_symbol(
    symbol: str,
    app: ConceptAppService = Depends(get_concept_app_service),
):
    """单股票所属概念列表（adata 实时拉取，**带入选理由 reason**）

    与 /by-symbol/{symbol} 的区别：
    - /by-symbol：从 DB 读，需要先 sync_concepts 落库
    - /live-by-symbol：从 adata 实时拉取（datacenter.eastmoney.com），
      无需先同步，每次返回最新；包含 `reason` 字段（如「公司有深圳国资背景。」）

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
            "🆕 08concept: 是否合并 adata 实时数据（带入选理由 reason）。"
            "默认 false（仅 DB）；true 时返回 is_merged=true 且 sections.concepts"
            " 携带 is_realtime / reason 字段"
        ),
    ),
    app: ConceptAppService = Depends(get_concept_app_service),
):
    """单股票所属概念 Tab 内容

    merge_live=false（默认）：
        返回 ConceptTabContentVO，仅含 DB 数据（06gainian 行为）。

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
    "/{name}",
    response_model=None,
    summary="单概念详情",
)
async def get_concept_detail(
    name: str,
    source: str = Query("ths", description="09concept: 默认改为 ths"),
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
    source: str = Query("ths", description="09concept: 默认改为 ths"),
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
    last_synced_at = await repo.get_last_synced_at(source="ths")  # 09concept: 默认 ths
    total = await repo.count_concepts(source="ths", is_active=True)
    return R.ok({
        "last_synced_at": (
            last_synced_at.isoformat() if last_synced_at else None
        ),
        "active_concepts": total,
    })


# ═══════════════════════════════════════════════════════════════════════════════
#  09concept 新增端点
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/{name}/snapshot",
    response_model=None,
    summary="取单概念最新行情快照（用于主概念 Tag 涨跌染色）",
)
async def get_concept_snapshot(
    name: str,
    db: AsyncSession = Depends(get_db),
):
    """取指定概念最新一条行情快照（09concept 新增）

    返回 dict（含 pct_change / rank_label / up_down_label / color 等），
    缺失则返回空对象 {}（前端按"暂无数据"展示）。
    """
    repo = ConceptRepoImpl(db)
    snap = await repo.list_latest_snapshot(concept_name=name)
    return R.ok(snap or {})


@router.get(
    "/snapshots/batch",
    response_model=None,
    summary="批量取多个概念的最新行情快照（避免 N+1）",
)
async def get_concept_snapshots_batch(
    names: str = Query(..., description="概念名列表，逗号分隔，如 白酒概念,超级品牌,西部大开发"),
    db: AsyncSession = Depends(get_db),
):
    """批量取多个概念的最新行情快照（09concept 新增）

    用于主概念 Tag 批量染色：单次 SQL 拿到 N 个概念的 pct_change，
    避免在 StockInfoList with_concepts=true 时 N+1 查询。
    """
    repo = ConceptRepoImpl(db)
    name_list = [n.strip() for n in names.split(",") if n.strip()]
    snaps = await repo.list_snapshots_for_names(names=name_list)
    # 缺失的概念返回空 dict
    out = {n: snaps.get(n, {}) for n in name_list}
    return R.ok(out)


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


@router.post(
    "/sync/membership",
    response_model=None,
    summary="触发 M:N 成分股反查同步任务（采集管理 UI 用）",
)
async def sync_membership(body: Optional[dict] = None):
    """触发 stock→concept 反查累加任务（09concept 新增）

    转发到通用 /collect/tasks 端点，避免重复 task_id 写入逻辑。
    Body: { "limit": int 可选 }
    """
    params = body or {}
    return R.ok({
        "task_type": "concept_membership",
        "params": params,
        "message": "请用 POST /collect/tasks 调用",
    })


@router.post(
    "/sync/snapshot",
    response_model=None,
    summary="触发概念行情快照采集任务（采集管理 UI 用）",
)
async def sync_snapshot_task(body: Optional[dict] = None):
    """触发 375 个概念行情采集任务（09concept 新增）"""
    params = body or {}
    return R.ok({
        "task_type": "concept_snapshot",
        "params": params,
        "message": "请用 POST /collect/tasks 调用",
    })


@router.post(
    "/sync/index-th",
    response_model=None,
    summary="触发概念指数日 K 采集任务（采集管理 UI 用）",
)
async def sync_index_th_task(body: Optional[dict] = None):
    """触发概念指数日 K 采集任务（09concept 新增，P1 功能）"""
    params = body or {}
    return R.ok({
        "task_type": "concept_index_th",
        "params": params,
        "message": "请用 POST /collect/tasks 调用",
    })
