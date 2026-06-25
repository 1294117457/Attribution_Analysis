"""K线数据 API"""

from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.kline import KLineResponse, KLineQueryRequest, KLineListResponse
from app.services.kline_service import KLineService
from app.services.collector_service import CollectorService

router = APIRouter()


@router.get("", response_model=List[KLineResponse], summary="获取K线历史")
async def get_klines(
    symbol: str = Query(..., description="股票代码", examples=["600519"]),
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    db: Session = Depends(get_db),
):
    """获取指定股票指定日期范围的K线历史数据"""
    service = KLineService(db)
    klines = service.get_by_date_range(symbol, start_date, end_date)
    return [service.to_response(k) for k in klines]


@router.post("/query", response_model=List[KLineResponse], summary="查询K线")
async def query_klines(
    request: KLineQueryRequest,
    db: Session = Depends(get_db),
):
    """通过请求体查询K线数据"""
    service = KLineService(db)
    klines = service.get_by_date_range(request.symbol, request.start_date, request.end_date)
    return [service.to_response(k) for k in klines]


@router.get("/{symbol}", response_model=KLineResponse, summary="获取单条K线")
async def get_kline(
    symbol: str,
    trade_date: date = Query(..., description="交易日期"),
    db: Session = Depends(get_db),
):
    """获取指定股票指定日期的K线数据"""
    service = KLineService(db)
    kline = service.get_by_code_and_date(symbol, trade_date)
    if not kline:
        raise HTTPException(status_code=404, detail=f"股票 {symbol} 在 {trade_date} 无数据")
    return service.to_response(kline)


@router.get("/{symbol}/latest", response_model=List[KLineResponse], summary="获取最近K线")
async def get_latest_klines(
    symbol: str,
    limit: int = Query(100, ge=1, le=500, description="返回条数"),
    db: Session = Depends(get_db),
):
    """获取指定股票最近N条K线"""
    service = KLineService(db)
    klines = service.get_latest(symbol, limit)
    return [service.to_response(k) for k in klines]


@router.post("/collect", summary="采集K线数据（后台）")
async def collect_klines(
    symbol: str = Query(..., description="股票代码"),
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    background_tasks: BackgroundTasks = BackgroundTasks,
    db: Session = Depends(get_db),
):
    """从 AkShare 采集K线数据（后台异步执行）"""
    service = CollectorService(db)
    background_tasks.add_task(service.collect_klines, symbol, start_date, end_date)
    return {
        "message": f"开始采集 {symbol} K线数据",
        "symbol": symbol,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "status": "pending",
    }
