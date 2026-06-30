"""数据管道 schemas"""

from data.schemas.base import BaseData
from data.schemas.kline import DailyKline, StockInfo

__all__ = ["BaseData", "DailyKline", "StockInfo"]
