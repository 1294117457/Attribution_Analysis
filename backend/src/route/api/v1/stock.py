"""股票 API 路由

⚠️ 历史说明：
    旧版 GET / （分页 + 4 表快照 + 池信息）已迁移至
    application/panel_service.py::StockPanelAppService +
    route/api/v1/panel.py::GET /api/v1/stock-panel/。

    本文件保留 GET / 作为**向后兼容薄包装**，内部委托给
    StockPanelAppService.query_panels，便于旧调用方（如 Dashboard）
    无需修改即可继续工作。

新代码请使用 GET /api/v1/stock-panel/。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.panel import StockPanelQueryRequest
from application.dto.stock import StockUpdateRequest
from application.panel_service import StockPanelAppService
from application.stock_service import StockAppService
from infrastructure.collectors import get_registry
from infrastructure.collectors.protocols import (
    DailyBasicFetcher,
    StockBasicFetcher,
)
from infrastructure.database.connection import get_db
from route.schemas import response as R

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stocks", tags=["股票"])


# ── 依赖注入工厂 ──────────────────────────────────────────

def get_stock_service(
    db: AsyncSession = Depends(get_db),
) -> StockAppService:
    return StockAppService(session=db)


def get_panel_service(
    db: AsyncSession = Depends(get_db),
) -> StockPanelAppService:
    """面板应用服务（兼容旧 /stocks/ 路由委托使用）"""
    return StockPanelAppService(session=db)


@lru_cache
def get_stock_fetcher() -> StockBasicFetcher:
    """股票基本信息采集器（单例）— 与 K 线共用 Tushare"""
    return get_registry().get(StockBasicFetcher)


@lru_cache
def get_daily_basic_fetcher() -> DailyBasicFetcher:
    """日频估值采集器（单例）— 与 K 线共用 Tushare"""
    return get_registry().get(DailyBasicFetcher)


# ── 查询路由 ──────────────────────────────────────────────

@router.get(
    "/",
    summary="股票列表（向后兼容，已迁移至 /stock-panel/）",
    deprecated=True,
)
async def query_stocks(
    q: Optional[str] = Query(None, description="代码 / 名称模糊搜索"),
    industry: Optional[str] = Query(None, description="行业"),
    market: Optional[str] = Query(None, description="市场类型"),
    exchange: Optional[str] = Query(None, description="交易所 SSE/SZSE/BSE"),
    is_hs: Optional[str] = Query(None, description="沪深港通 N/H/S"),
    list_status: Optional[str] = Query("L", description="上市状态 L/D/P/全部"),
    exclude_st: Optional[bool] = Query(None, description="排除ST股票"),
    min_total_mv: Optional[float] = Query(None, ge=0, description="最低总市值(万元)"),
    with_pools: bool = Query(False, description="是否附带所属操作池（避免 N+1 反向查询）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=500, description="每页条数"),
    panel_service: StockPanelAppService = Depends(get_panel_service),
):
    """⚠️ 已废弃：迁移至 GET /api/v1/stock-panel/

    本路由保留为**向后兼容薄包装**，内部委托 StockPanelAppService.query_panels。
    新代码请直接使用 /api/v1/stock-panel/，字段与响应完全一致。
    """
    request = StockPanelQueryRequest(
        q=q,
        industry=industry,
        market=market,
        exchange=exchange,
        is_hs=is_hs,
        list_status=list_status,
        exclude_st=exclude_st,
        min_total_mv=min_total_mv,
        with_pools=with_pools,
        page=page,
        page_size=page_size,
    )
    response = await panel_service.query_panels(request)
    return R.ok(response.model_dump())


@router.get("/meta", summary="股票枚举值")
async def get_stock_meta(
    service: StockAppService = Depends(get_stock_service),
):
    """获取行业 / 市场 / 交易所枚举值（用于前端筛选下拉）"""
    meta = await service.get_meta()
    return R.ok(meta.model_dump())


@router.get("/{symbol}", summary="股票详情")
async def get_stock(
    symbol: str,
    service: StockAppService = Depends(get_stock_service),
):
    """获取股票详细信息"""
    stock = await service.get_stock(symbol)
    return R.ok(stock.model_dump())


# ── 写入路由 ──────────────────────────────────────────────

@router.post(
    "/",
    summary="新增/更新股票",
    status_code=status.HTTP_201_CREATED,
)
async def upsert_stock(
    symbol: str = Query(..., description="股票代码"),
    name: str = Query(..., description="股票名称"),
    industry: Optional[str] = Query(None, description="所属行业"),
    market: Optional[str] = Query(None, description="所属市场"),
    service: StockAppService = Depends(get_stock_service),
):
    """新增或更新股票信息"""
    stock = await service.upsert_stock(symbol, name, industry, market)
    return R.created(stock.model_dump())


@router.post(
    "/sync",
    summary="同步股票基本信息",
    status_code=status.HTTP_201_CREATED,
)
async def sync_stocks(
    list_status: str = Query("L", description="上市状态 L/D/P"),
    service: StockAppService = Depends(get_stock_service),
    fetcher: StockBasicFetcher = Depends(get_stock_fetcher),
):
    """全量同步 A股股票基本信息

    从 Tushare 拉取股票基本信息并 upsert 到数据库。
    同步完成后，前端可调用 /stocks/meta 刷新枚举值。
    """
    result = await service.sync_stocks(fetcher, list_status=list_status)
    return R.created(result.model_dump())


@router.patch("/{symbol}", summary="部分更新股票")
async def update_stock(
    symbol: str,
    request: StockUpdateRequest,
    service: StockAppService = Depends(get_stock_service),
):
    """部分更新股票信息"""
    stock = await service.update_stock(symbol, request)
    return R.ok(stock.model_dump())


# ── 删除路由 ──────────────────────────────────────────────

@router.delete("/{symbol}", summary="删除股票")
async def delete_stock(
    symbol: str,
    service: StockAppService = Depends(get_stock_service),
):
    """删除股票"""
    response = await service.delete_stock(symbol)
    return R.ok(response.model_dump())


# ── 日频估值同步 ──────────────────────────────────────────

@router.post("/sync-daily-basic", summary="同步日频估值指标")
async def sync_daily_basic(
    trade_date: Optional[str] = Query(
        None,
        description="YYYYMMDD 格式，不传默认取最近交易日",
    ),
    days: int = Query(1, ge=1, le=30, description="往回拉取天数（默认1天）"),
    db: AsyncSession = Depends(get_db),
    fetcher: DailyBasicFetcher = Depends(get_daily_basic_fetcher),
):
    """从 Tushare daily_basic 同步全市场日频估值

    用于填充 fin_daily_basics 表，使股票列表能展示最新价、总市值、PE 等。
    """
    from infrastructure.repositories.fin_daily_basic_repository import FinDailyBasicRepoImpl

    repo = FinDailyBasicRepoImpl(db)

    if trade_date:
        dates_to_sync = [trade_date]
    else:
        today = date.today()
        dates_to_sync = [
            (today - timedelta(days=i)).strftime("%Y%m%d")
            for i in range(days)
        ]

    total_synced = 0
    synced_dates: list[str] = []

    for td in dates_to_sync:
        bo_list = await asyncio.to_thread(fetcher.fetch_daily_basic, td)
        if not bo_list:
            logger.info("daily_basic %s: 无数据（可能非交易日）", td)
            continue
        entities = [bo.to_entity() for bo in bo_list]
        count = await repo.save_batch(entities)
        total_synced += count
        synced_dates.append(td)
        logger.info("daily_basic %s: 写入 %d 条", td, count)

    return R.ok({
        "synced_count": total_synced,
        "dates": synced_dates,
        "message": f"成功同步 {total_synced} 条日频估值数据",
    })