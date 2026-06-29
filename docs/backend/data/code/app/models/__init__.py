"""数据库模型"""

from app.models.base import TimestampMixin
from app.models.stock import StockKlineDB

__all__ = ["TimestampMixin", "StockKlineDB"]
