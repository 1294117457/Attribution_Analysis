"""数据采集模块"""

from data.schemas import StockKline, StockKlineResponse
from data.akshare_client import AkShareClient
from data.service import DataService

__all__ = [
    "StockKline",
    "StockKlineResponse",
    "AkShareClient",
    "DataService",
]
