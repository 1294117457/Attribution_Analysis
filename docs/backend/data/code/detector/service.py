"""异常检测服务"""

from datetime import date
from typing import Optional

from detector.price_detector import PriceDetector
from detector.volume_detector import VolumeDetector
from detector.base import DetectionResult


class DetectorService:
    """异常检测服务"""

    def __init__(self):
        self.price_detector = PriceDetector(threshold=0.7)
        self.volume_detector = VolumeDetector(threshold=0.7)

    def detect_price_anomaly(
        self,
        prices: list[float],
        dates: list[date],
        method: str = "zscore",
    ) -> DetectionResult:
        """检测价格异常"""
        detector = PriceDetector(
            threshold=0.7,
            method=method,
            lookback=20,
        )
        result = detector.detect(prices, dates)
        return result

    def detect_volume_anomaly(
        self,
        volumes: list[float],
        dates: list[date],
    ) -> DetectionResult:
        """检测成交量异常"""
        result = self.volume_detector.detect(volumes, dates)
        return result

    def detect_anomaly(
        self,
        symbol: str,
        prices: list[float],
        volumes: list[float],
        dates: list[date],
    ) -> dict:
        """综合异常检测"""
        price_result = self.detect_price_anomaly(prices, dates)
        volume_result = self.detect_volume_anomaly(volumes, dates)

        return {
            "symbol": symbol,
            "price_anomalies": price_result,
            "volume_anomalies": volume_result,
            "summary": self._generate_summary(price_result, volume_result),
        }

    def _generate_summary(
        self,
        price_result: DetectionResult,
        volume_result: DetectionResult,
    ) -> str:
        """生成摘要"""
        parts = []

        if price_result.anomaly_count > 0:
            parts.append(
                f"发现 {price_result.anomaly_count} 个价格异常"
            )

        if volume_result.anomaly_count > 0:
            parts.append(
                f"发现 {volume_result.anomaly_count} 个成交量异常"
            )

        if not parts:
            return "未发现异常"

        return "，".join(parts)
