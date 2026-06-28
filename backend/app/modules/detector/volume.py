"""
量能异常检测器。
基于 IQR（四分位距）算法检测成交量异常。
"""

import statistics
from typing import Optional

from app.modules.detector.base import BaseDetector, DetectionResult, Severity
from app.modules.config import DetectorConfig


class VolumeDetector(BaseDetector):
    """量能异常检测器（IQR）"""

    name = "volume"

    def __init__(self, config: Optional[DetectorConfig] = None):
        super().__init__()
        self.config = config or DetectorConfig()
        self.k = self.config.iqr_k  # IQR 倍数，默认 1.5
        self.lookback_days = self.config.iqr_lookback_days

    def detect(self, current: dict, history: list[dict]) -> DetectionResult:
        """
        检测量能异常。

        算法：IQR（四分位距）
        1. 计算 Q1（25%分位）和 Q3（75%分位）
        2. IQR = Q3 - Q1
        3. 正常范围：[Q1 - k×IQR, Q3 + k×IQR]
        4. 超出范围 → 异常（放量或缩量）
        """
        volume = current.get("volume")

        if volume is None or volume <= 0:
            return DetectionResult(
                detector_name=self.name,
                is_anomaly=False,
                severity=Severity.NORMAL,
                score=0.0,
                reason="无成交量数据",
            )

        if len(history) < 10:
            return DetectionResult(
                detector_name=self.name,
                is_anomaly=False,
                severity=Severity.NORMAL,
                score=0.0,
                reason="历史数据不足",
            )

        # 提取历史成交量
        volumes = [h.get("volume", 0) for h in history if h.get("volume") and h.get("volume") > 0]

        if len(volumes) < 10:
            return DetectionResult(
                detector_name=self.name,
                is_anomaly=False,
                severity=Severity.NORMAL,
                score=0.0,
                reason="有效历史数据不足",
            )

        # 计算分位数
        sorted_volumes = sorted(volumes)
        q1 = self._percentile(sorted_volumes, 25)
        q3 = self._percentile(sorted_volumes, 75)
        iqr = q3 - q1

        # 计算正常范围
        lower_bound = q1 - self.k * iqr
        upper_bound = q3 + self.k * iqr

        # 计算成交量比率
        avg_volume = statistics.mean(volumes)
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0

        # 判断异常
        is_anomaly = volume < lower_bound or volume > upper_bound

        # 计算异常分数
        if is_anomaly:
            if volume > upper_bound:
                # 放量
                score = min(1.0, 0.5 + 0.3 * (volume_ratio - 1.0))
            else:
                # 缩量
                score = min(0.8, 0.4 + 0.3 * (1.0 - volume_ratio))
        else:
            score = 0.0

        # 判断严重程度
        if volume > upper_bound * 3 or volume < lower_bound * 0.3:
            severity = Severity.CRITICAL
        elif volume > upper_bound * 2 or volume < lower_bound * 0.5:
            severity = Severity.HIGH
        elif volume > upper_bound * 1.5 or volume < lower_bound * 0.7:
            severity = Severity.MEDIUM
        elif is_anomaly:
            severity = Severity.LOW
        else:
            severity = Severity.NORMAL

        # 生成原因描述
        if volume > upper_bound:
            reason = f"成交量放大 {volume_ratio:.1f} 倍（超过 Q3+{self.k}×IQR）"
        elif volume < lower_bound:
            reason = f"成交量萎缩至 {volume_ratio:.1f} 倍（低于 Q1-{self.k}×IQR）"
        else:
            reason = f"成交量正常（当日 {volume_ratio:.1f}x 均量）"

        return DetectionResult(
            detector_name=self.name,
            is_anomaly=is_anomaly,
            severity=severity,
            score=score,
            reason=reason,
            details={
                "volume": volume,
                "volume_ratio": round(volume_ratio, 2),
                "q1": round(q1, 0),
                "q3": round(q3, 0),
                "iqr": round(iqr, 0),
                "lower_bound": round(lower_bound, 0),
                "upper_bound": round(upper_bound, 0),
            },
        )

    @staticmethod
    def _percentile(sorted_data: list, p: float) -> float:
        """计算百分位数"""
        n = len(sorted_data)
        k = (n - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < n else f
        return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])
