from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.anomaly_service import AnomalyService
from app.schemas.anomaly import (
    AnomalyCreate,
    AnomalyResponse,
    AnomalyListResponse,
)
from datetime import date

router = APIRouter(prefix="/anomalies", tags=["异常"])


@router.post("", response_model=AnomalyResponse)
def create_anomaly(
    data: AnomalyCreate,
    db: Session = Depends(get_db),
):
    """创建异常记录"""
    service = AnomalyService(db)
    return service.create(data)


@router.get("/stock/{symbol}", response_model=AnomalyListResponse)
def list_anomalies(
    symbol: str,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: Session = Depends(get_db),
):
    """查询股票的异常记录"""
    service = AnomalyService(db)
    items = service.list_by_symbol(symbol, start_date, end_date)
    return AnomalyListResponse(total=len(items), items=items)
