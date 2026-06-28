"""
异常检测模块。
提供价格、量能、波动、趋势异常检测功能。
"""

from app.modules.detector.base import BaseDetector, DetectionResult, Severity
from app.modules.detector.price import PriceDetector
from app.modules.detector.volume import VolumeDetector
from app.modules.detector.volatility import VolatilityDetector
from app.modules.detector.trend import TrendDetector
from app.modules.detector.aggregator import DetectorAggregator
from app.modules.detector.service import DetectorService

__all__ = [
    "BaseDetector",
    "DetectionResult",
    "Severity",
    "PriceDetector",
    "VolumeDetector",
    "VolatilityDetector",
    "TrendDetector",
    "DetectorAggregator",
    "DetectorService",
]
