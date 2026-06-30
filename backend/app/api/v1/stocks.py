"""日K线数据端点"""

from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from infra.database.connection import get_db_session
from app.schemas.stock import (
    DailyKlineResponse,
    DailyKlineListResponse,
    CollectRequest,
    CollectResponse,
)
from data.services.stock_service import StockService


router = APIRouter(prefix="/stocks", tags=["日K线数据"])


@router.get("/", response_model=DailyKlineListResponse)
def list_klines(
    symbol: str = Query(..., description="股票代码，如 000001"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(365, ge=1, le=1000, description="返回数量"),
    db: Session = Depends(get_db_session),
):
    """查询日K线数据"""
    service = StockService(db)
    klines = service.get_klines(symbol, start_date, end_date, limit)
    return DailyKlineListResponse(total=len(klines), items=klines)


@router.get("/{symbol}", response_model=DailyKlineListResponse)
def get_stock_klines(
    symbol: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(365, ge=1, le=1000),
    db: Session = Depends(get_db_session),
):
    """获取指定股票的日K线数据"""
    service = StockService(db)
    klines = service.get_klines(symbol, start_date, end_date, limit)
    return DailyKlineListResponse(total=len(klines), items=klines)


@router.post("/collect", response_model=CollectResponse)
def collect_stock(
    request: CollectRequest,
    db: Session = Depends(get_db_session),
):
    """采集并存储日K线数据"""
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
