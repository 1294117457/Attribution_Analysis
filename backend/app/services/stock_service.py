"""股票数据服务 - API 层"""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from data.services import StockService as DataStockService
from app.database.models import StockKlineDB


class StockService:
    """股票服务（API 层）"""

    def __init__(self, db: Session):
        self.db = db
        self._data_service = None

    @property
    def data_service(self) -> DataStockService:
        """懒加载数据服务"""
        if self._data_service is None:
            self._data_service = DataStockService(self.db)
        return self._data_service

    def get_klines(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 365,
    ) -> list[StockKlineDB]:
        """获取 K 线数据"""
        return self.data_service.get_klines(symbol, start_date, end_date, limit)

    def collect_and_save(
        self,
        symbol: str,
        days: int = 365,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> int:
        """采集并存储"""
        return self.data_service.collect_and_save(symbol, days, start_date, end_date)
