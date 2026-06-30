"""数据采集模块"""

from data.fetchers.akshare_fetcher import AkShareFetcher
from data.schemas import StockKline

__all__ = ["AkShareFetcher", "StockKline"]
