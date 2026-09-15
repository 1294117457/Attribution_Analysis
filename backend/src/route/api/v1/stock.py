"""股票 API 路由"""

from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.stock import StockQueryRequest, StockUpdateRequest
from application.stock_service import StockAppService
from infrastructure.collectors.interfaces import FetcherProtocol
from infrastructure.config import get_settings
from infrastructure.database.connection import get_db
from route.schemas import response as R

router = APIRouter(prefix="/stocks", tags=["股票"])


# ── 依赖注入工厂 ──────────────────────────────────────────

def get_stock_service(
    db: AsyncSession = Depends(get_db),
) -> StockAppService:
    return StockAppService(session=db)


@lru_cache
def get_stock_fetcher() -> FetcherProtocol:
    """股票基本信息采集器（单例）。

    与 K线采集器共用同一数据源（tushare/akshare）。
    """
    source = (get_settings().COLLECTOR_SOURCE or "akshare").lower()
    if source == "tushare":
        from infrastructure.collectors.tushare import TushareFetcher
        from domain.kline.schemas import KlineBO
        return TushareFetcher(KlineBO)
    from infrastructure.collectors.akshare import AkShareFetcher
    from domain.kline.schemas import KlineBO
    return AkShareFetcher(KlineBO)


# ── 查询路由 ──────────────────────────────────────────────

@router.get("/", summary="股票列表（分页+多维筛选）")
async def query_stocks(
    q: Optional[str] = Query(None, description="代码 / 名称模糊搜索"),
    industry: Optional[str] = Query(None, description="行业"),
    market: Optional[str] = Query(None, description="市场类型"),
    exchange: Optional[str] = Query(None, description="交易所 SSE/SZSE/BSE"),
    is_hs: Optional[str] = Query(None, description="沪深港通 N/H/S"),
    list_status: Optional[str] = Query("L", description="上市状态 L/D/P/全部"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=500, description="每页条数"),
    service: StockAppService = Depends(get_stock_service),
):
    """分页 + 多维筛选 + K线统计的股票列表（StockPanel.vue 主列表用）"""
    request = StockQueryRequest(
        q=q,
        industry=industry,
        market=market,
        exchange=exchange,
        is_hs=is_hs,
        list_status=list_status,
        page=page,
        page_size=page_size,
    )
    response = await service.query_stocks(request)
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
    fetcher: FetcherProtocol = Depends(get_stock_fetcher),
):
    """全量同步 A股股票基本信息

    从 Tushare/AkShare 拉取股票基本信息并 upsert 到数据库。
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
