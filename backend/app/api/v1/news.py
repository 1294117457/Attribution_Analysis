"""新闻数据 API"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()


@router.get("", summary="获取新闻列表")
async def get_news(
    symbol: str = Query(None, description="股票代码"),
    limit: int = Query(20, ge=1, le=100, description="返回条数"),
    db: Session = Depends(get_db),
):
    """获取新闻列表（预留接口）"""
    # TODO: 实现新闻查询
    return {
        "total": 0,
        "data": [],
        "message": "新闻功能开发中"
    }


@router.get("/{symbol}", summary="获取股票新闻")
async def get_stock_news(
    symbol: str,
    limit: int = Query(20, ge=1, le=100, description="返回条数"),
    db: Session = Depends(get_db),
):
    """获取指定股票的新闻"""
    # TODO: 实现股票新闻查询
    return {
        "symbol": symbol,
        "total": 0,
        "data": [],
        "message": "新闻功能开发中"
    }
