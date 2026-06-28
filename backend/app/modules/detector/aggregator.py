"""
检测结果聚合器。
综合多个检测器的结果，计算最终异常分数和等级。
"""

from typing import Optional

from app.modules.detector.base import DetectionResult, Severity
from app.modules.config import DetectorConfig


class DetectorAggregator:
    """检测结果聚合器"""

    def __init__(self, config: Optional[DetectorConfig] = None):
        self.config = config or DetectorConfig()

    def aggregate(self, results: list[DetectionResult]) -> dict:
        """
        聚合多个检测器的结果。

        Args:
            results: 各检测器的检测结果列表

        Returns:
            dict: 聚合后的综合结果
        """
        # 获取权重
        weights = {
            "price": self.config.zscore_weight,
            "volume": self.config.iqr_weight,
            "volatility": self.config.volatility_weight,
            "trend": self.config.trend_weight,
        }

        # 筛选异常检测器
        anomaly_results = [r for r in results if r.is_anomaly]

        # 计算加权分数
        total_score = 0.0
        for result in results:
            weight = weights.get(result.detector_name, 0.25)
            total_score += result.score * weight

        # 获取最高严重程度
        max_severity = Severity.NORMAL
        severity_order = {
            Severity.CRITICAL: 4,
            Severity.HIGH: 3,
            Severity.MEDIUM: 2,
            Severity.LOW: 1,
            Severity.NORMAL: 0,
        }

        for result in results:
            severity_value = severity_order.get(result.severity, 0)
            max_severity_value = severity_order.get(max_severity, 0)
            if severity_value > max_severity_value:
                max_severity = result.severity

        # 判断是否异常
        is_anomaly = len(anomaly_results) > 0

        # 判断综合等级
        final_severity = self._get_final_severity(total_score, len(anomaly_results))

        # 生成综合原因
        if anomaly_results:
            reasons = [r.reason for r in anomaly_results]
            reason = "；".join(reasons[:3])  # 最多3条
        else:
            reason = "无异常"

        return {
            "is_anomaly": is_anomaly,
            "severity": final_severity,
            "score": round(total_score, 3),
            "anomaly_count": len(anomaly_results),
            "triggers": [
                {
                    "detector": r.detector_name,
                    "reason": r.reason,
                    "severity": r.severity.value,
                    "score": round(r.score, 3),
                }
                for r in anomaly_results
            ],
            "details": {
                "scores": {
                    r.detector_name: round(r.score, 3)
                    for r in results
                },
                "weights": weights,
            },
        }

    def _get_final_severity(self, score: float, anomaly_count: int) -> str:
        """根据综合分数和异常数量判断最终等级"""
        if score >= self.config.severity_critical:
            return "critical"
        elif score >= self.config.severity_high:
            return "high"
        elif score >= self.config.severity_medium:
            return "medium"
        elif score > 0:
            return "low"
        else:
            return "normal"
