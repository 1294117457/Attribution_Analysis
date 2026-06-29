"""数据库模型"""

from app.database.models.base import TimestampMixin
from app.database.models.stock import StockKlineDB

__all__ = ["TimestampMixin", "StockKlineDB"]
