"""依赖注入"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.stock_service import StockService


def get_stock_service(db: Session = Depends(get_db)) -> StockService:
    """获取股票服务"""
    return StockService(db)
