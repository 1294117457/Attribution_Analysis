"""数据采集模块"""

from data.adapters.akshare import AkShareFetcher
from data.schemas import DailyKline

__all__ = ["AkShareFetcher", "DailyKline"]
