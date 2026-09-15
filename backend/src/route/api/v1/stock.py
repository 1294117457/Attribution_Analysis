"""股票 API 路由"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.stock import StockUpdateRequest
from application.stock_service import StockAppService
from infrastructure.database.connection import get_db
from route.schemas import response as R

router = APIRouter(prefix="/stocks", tags=["股票"])


def get_stock_service(
    db: AsyncSession = Depends(get_db),
) -> StockAppService:
    return StockAppService(session=db)


# ── 查询路由 ──────────────────────────────────────────────

@router.get("/", summary="股票列表")
async def list_stocks(
    industry: Optional[str] = Query(None, description="按行业筛选"),
    market: Optional[str] = Query(None, description="按市场筛选（SH/SZ/BSE）"),
    service: StockAppService = Depends(get_stock_service),
):
    """获取所有已采集的股票列表（含K线统计）"""
    response = await service.list_stocks(industry=industry, market=market)
    return R.ok(response.model_dump())


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
