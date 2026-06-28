"""
异常检测服务。
整合各检测器和聚合器，提供统一的检测接口。
"""

from typing import Optional

from app.modules.collector.storage import KLineStorage
from app.modules.detector.base import BaseDetector, DetectionResult
from app.modules.detector.price import PriceDetector
from app.modules.detector.volume import VolumeDetector
from app.modules.detector.volatility import VolatilityDetector
from app.modules.detector.trend import TrendDetector
from app.modules.detector.aggregator import DetectorAggregator
from app.modules.config import DetectorConfig


class DetectorService:
    """异常检测服务"""

    def __init__(self, config: Optional[DetectorConfig] = None):
        self.config = config or DetectorConfig()
        self.storage = KLineStorage()

        # 初始化检测器
        self.detectors: list[BaseDetector] = [
            PriceDetector(self.config),
            VolumeDetector(self.config),
            VolatilityDetector(self.config),
            TrendDetector(self.config),
        ]

        # 聚合器
        self.aggregator = DetectorAggregator(self.config)

    def detect(
        self,
        code: str,
        trade_date: Optional[str] = None,
        lookback_days: int = 30,
    ) -> dict:
        """
        检测单只股票某日是否异常。

        Args:
            code: 股票代码
            trade_date: 交易日期（YYYY-MM-DD），默认最新日期
            lookback_days: 回看天数，默认30天

        Returns:
            dict: 检测结果
        """
        # 获取数据
        klines = self.storage.get_recent_klines(code, lookback_days + 10)

        if not klines:
            return {
                "code": code,
                "trade_date": trade_date,
                "is_anomaly": False,
                "severity": "normal",
                "score": 0.0,
                "error": "无K线数据",
            }

        # 按日期排序（升序）
        klines = sorted(klines, key=lambda x: str(x.get("date", "")))

        # 找到目标日期的数据
        if trade_date:
            target_klines = [k for k in klines if str(k.get("date", ""))[:10] == trade_date]
            if not target_klines:
                return {
                    "code": code,
                    "trade_date": trade_date,
                    "is_anomaly": False,
                    "severity": "normal",
                    "score": 0.0,
                    "error": f"无 {trade_date} 的K线数据",
                }
            target_kline = target_klines[0]
            # 历史数据（目标日期之前）
            history = [k for k in klines if str(k.get("date", ""))[:10] < trade_date]
        else:
            # 最新日期
            target_kline = klines[-1]
            history = klines[:-1]
            trade_date = str(target_kline.get("date", ""))[:10]

        # 逐个检测器检测
        results = []
        for detector in self.detectors:
            result = detector.detect(target_kline, history)
            results.append(result)

        # 聚合结果
        aggregated = self.aggregator.aggregate(results)

        return {
            "code": code,
            "name": target_kline.get("name", ""),
            "trade_date": trade_date,
            "is_anomaly": aggregated["is_anomaly"],
            "severity": aggregated["severity"],
            "score": aggregated["score"],
            "anomaly_count": aggregated["anomaly_count"],
            "triggers": aggregated["triggers"],
            "kline": {
                "open": target_kline.get("open"),
                "high": target_kline.get("high"),
                "low": target_kline.get("low"),
                "close": target_kline.get("close"),
                "volume": target_kline.get("volume"),
                "change_pct": target_kline.get("change_pct"),
            },
        }

    def detect_batch(
        self,
        codes: list[str],
        trade_date: Optional[str] = None,
    ) -> dict:
        """
        批量检测多只股票。

        Args:
            codes: 股票代码列表
            trade_date: 交易日期

        Returns:
            dict: 批量检测结果
        """
        results = []
        anomaly_count = 0

        for code in codes:
            result = self.detect(code, trade_date)
            if "error" not in result:
                results.append({
                    "code": result["code"],
                    "name": result.get("name", ""),
                    "is_anomaly": result["is_anomaly"],
                    "severity": result["severity"],
                    "score": result["score"],
                })
                if result["is_anomaly"]:
                    anomaly_count += 1

        return {
            "total": len(codes),
            "anomaly_count": anomaly_count,
            "results": results,
        }

    def get_detectors(self) -> list[str]:
        """获取所有检测器名称"""
        return [d.name for d in self.detectors]
