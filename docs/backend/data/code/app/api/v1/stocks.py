"""股票数据 API"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional

from app.database.connection import get_db
from app.services.stock_service import StockService
from data.schemas import StockKlineResponse, StockListResponse, CollectResponse

router = APIRouter(prefix="/stocks", tags=["股票"])


@router.get("/{symbol}", response_model=StockKlineResponse)
def get_stock(
    symbol: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    """获取股票 K 线数据"""
    service = StockService(db)
    data = service.get_stock(symbol, start_date, end_date)

    if not data:
        raise HTTPException(status_code=404, detail="股票数据不存在")

    return data


@router.get("/", response_model=StockListResponse)
def list_stocks(
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """获取股票列表"""
    service = StockService(db)
    items = service.list_stocks(limit)
    return StockListResponse(total=len(items), items=items)


@router.post("/collect", response_model=CollectResponse)
def collect_stock(
    symbol: str,
    days: int = Query(365, ge=1, le=3650),
    db: Session = Depends(get_db),
):
    """采集股票数据"""
    service = StockService(db)
    result = service.collect_stock(symbol, days)
    return result
