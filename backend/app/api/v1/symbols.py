"""股票列表 API"""

from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()


@router.get("", summary="获取A股股票列表")
async def get_stock_list(
    market: str = Query("A股", description="市场类型"),
    db: Session = Depends(get_db),
):
    """
    获取A股股票列表

    - **market**: 市场类型（A股、科创板、创业板等）
    """
    # TODO: 实现从数据库或 AkShare 获取股票列表
    return {
        "market": market,
        "total": 0,
        "data": [],
        "message": "股票列表功能开发中"
    }


@router.get("/search", summary="搜索股票")
async def search_stock(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    db: Session = Depends(get_db),
):
    """
    搜索股票

    - **keyword**: 搜索关键词（代码或名称）
    """
    # TODO: 实现股票搜索
    return {
        "keyword": keyword,
        "total": 0,
        "data": [],
        "message": "股票搜索功能开发中"
    }
