"""股票数据端点"""

from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from infra.database.connection import get_db
from app.schemas.stock import (
    DailyKlineListResponse,
    CollectRequest,
    CollectResponse,
    StockListResponse,
    StockInfoResponse,
    DeleteResponse,
)
from data.services.stock_service import StockService


router = APIRouter(prefix="/stocks", tags=["股票数据"])


# ============ 股票列表 ============

@router.get("/", response_model=StockListResponse)
def list_stocks(db: Session = Depends(get_db)):
    """获取所有已采集的股票列表"""
    service = StockService(db)
    stocks = service.list_stocks()
    return StockListResponse(total=len(stocks), items=stocks)


@router.get("/{symbol}", response_model=StockInfoResponse)
def get_stock(symbol: str, db: Session = Depends(get_db)):
    """获取股票详情"""
    service = StockService(db)
    info = service.get_stock_info(symbol)
    if not info:
        raise HTTPException(status_code=404, detail=f"股票 {symbol} 不存在")

    # 获取K线统计
    klines = service.get_klines(symbol, limit=1)
    return StockInfoResponse(
        symbol=info.symbol,
        name=info.name,
        industry=info.industry,
        market=info.market,
        list_date=info.list_date,
        total_shares=info.total_shares,
        record_count=len(klines),
    )


# ============ K线数据 ============

@router.get("/{symbol}/klines", response_model=DailyKlineListResponse)
def get_klines(
    symbol: str,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(365, ge=1, le=3650, description="返回数量"),
    db: Session = Depends(get_db),
):
    """获取股票的K线数据"""
    service = StockService(db)
    klines = service.get_klines(symbol, start_date, end_date, limit)
    return DailyKlineListResponse(total=len(klines), items=klines)


# ============ 采集 ============

@router.post("/collect", response_model=CollectResponse)
def collect_stock(
    request: CollectRequest,
    db: Session = Depends(get_db),
):
    """采集并存储股票数据"""
    service = StockService(db)
    try:
        count, name = service.collect_and_save(
            symbol=request.symbol,
            days=request.days,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        if count == 0:
            return CollectResponse(
                status="failed",
                symbol=request.symbol,
                name=name or None,
                count=0,
                message="未获取到新数据（可能已采集或代码无效）",
            )
        return CollectResponse(
            status="success",
            symbol=request.symbol,
            name=name,
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


# ============ 删除 ============

@router.delete("/{symbol}", response_model=DeleteResponse)
def delete_stock(symbol: str, db: Session = Depends(get_db)):
    """删除股票的所有数据"""
    service = StockService(db)
    deleted = service.delete_stock(symbol)

    if deleted == 0:
        raise HTTPException(status_code=404, detail=f"股票 {symbol} 不存在或无数据")

    return DeleteResponse(
        status="success",
        symbol=symbol,
        deleted_count=deleted,
        message=f"成功删除 {deleted} 条数据",
    )


@router.delete("/{symbol}/klines/{date_str}", response_model=DeleteResponse)
def delete_kline(symbol: str, date_str: str, db: Session = Depends(get_db)):
    """删除单条K线数据"""
    try:
        del_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")

    service = StockService(db)
    deleted = service.delete_kline(symbol, del_date)

    if deleted == 0:
        raise HTTPException(
            status_code=404, detail=f"股票 {symbol} 在 {date_str} 无数据"
        )

    return DeleteResponse(
        status="success",
        symbol=symbol,
        deleted_count=deleted,
        message=f"成功删除 {deleted} 条数据",
    )
