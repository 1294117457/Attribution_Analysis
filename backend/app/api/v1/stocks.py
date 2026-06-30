"""股票数据端点"""

from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db_session
from app.schemas.stock import (
    StockKlineResponse,
    StockKlineListResponse,
    CollectRequest,
    CollectResponse,
)
from data.services.stock_service import StockService


router = APIRouter(prefix="/stocks", tags=["股票数据"])


@router.get("/", response_model=StockKlineListResponse)
def list_klines(
    symbol: str = Query(..., description="股票代码，如 000001"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(365, ge=1, le=1000, description="返回数量"),
    db: Session = Depends(get_db_session),
):
    """获取 K 线数据"""
    service = StockService(db)
    klines = service.get_klines(symbol, start_date, end_date, limit)
    return StockKlineListResponse(total=len(klines), items=klines)


@router.get("/{symbol}", response_model=StockKlineListResponse)
def get_stock_klines(
    symbol: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(365, ge=1, le=1000),
    db: Session = Depends(get_db_session),
):
    """获取指定股票的 K 线数据"""
    service = StockService(db)
    klines = service.get_klines(symbol, start_date, end_date, limit)
    return StockKlineListResponse(total=len(klines), items=klines)


@router.post("/collect", response_model=CollectResponse)
def collect_stock(
    request: CollectRequest,
    db: Session = Depends(get_db_session),
):
    """采集股票数据"""
    service = StockService(db)
    try:
        count = service.collect_and_save(
            symbol=request.symbol,
            days=request.days,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        return CollectResponse(
            status="success",
            symbol=request.symbol,
            count=count,
            message=f"成功采集并存储 {count} 条数据",
        )
    except Exception as e:
        return CollectResponse(
            status="failed",
            symbol=request.symbol,
            count=0,
            message=str(e),
        )
