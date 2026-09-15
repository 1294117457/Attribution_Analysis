"""AkShare 数据源"""

from infrastructure.collectors.akshare.fetcher import AkShareFetcher
from infrastructure.collectors.akshare.parser import KlineParser

__all__ = ["AkShareFetcher", "KlineParser"]
