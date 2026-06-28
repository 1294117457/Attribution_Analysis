"""
数据采集模块。
提供股票数据采集、存储功能。
"""

from app.modules.collector.service import CollectorService
from app.modules.collector.storage import KLineStorage

__all__ = ["CollectorService", "KLineStorage"]
