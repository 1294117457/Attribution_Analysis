"""成交量异常检测器"""

import statistics
from datetime import date

from detector.base import BaseDetector, AnomalyResult, DetectionResult


class VolumeDetector(BaseDetector):
    """
    成交量异常检测器

    检测成交量突刺：
    1. 超过历史平均 N 倍
    2. 超过历史均值 + 2*标准差
    """

    def __init__(
        self,
        threshold: float = 0.8,
        multiplier: float = 2.0,
        lookback: int = 20,
    ):
        """
        Args:
            threshold: 异常阈值
            multiplier: 超过均值多少倍视为异常
            lookback: 回看周期
        """
        super().__init__(threshold)
        self.multiplier = multiplier
        self.lookback = lookback

    def detect(
        self,
        volumes: list[int | float],
        dates: list[date],
    ) -> DetectionResult:
        """检测成交量异常"""
        if len(volumes) < self.lookback:
            raise ValueError(f"数据量不足，需要至少 {self.lookback} 个数据点")

        anomalies = []
        total_count = len(volumes)

        for i in range(self.lookback, total_count):
            history = volumes[i - self.lookback : i]
            current = volumes[i]
            current_date = dates[i]

            score, is_anomaly = self._detect_point(current, history)

            if is_anomaly:
                result = AnomalyResult(
                    date=current_date,
                    value=float(current),
                    score=score,
                    is_anomaly=True,
                    type="volume_spike",
                    threshold=self.threshold,
                    description=self._describe_anomaly(current, history, score),
                )
                anomalies.append(result)

        return DetectionResult(
            symbol="",
            start_date=dates[0],
            end_date=dates[-1],
            anomalies=anomalies,
            total_count=total_count,
            anomaly_count=len(anomalies),
        )

    def _detect_point(
        self,
        current: float,
        history: list[float],
    ) -> tuple[float, bool]:
        """检测单个点"""
        mean = statistics.mean(history)
        std = statistics.stdev(history) if len(history) > 1 else 0

        if mean == 0:
            return 0.0, False

        # 计算倍数
        ratio = current / mean

        # 计算分数：超过 multiplier 倍给高分
        if ratio >= self.multiplier:
            score = min((ratio - self.multiplier + 1) / 2, 1.0)
        else:
            score = 0.0

        return score, score >= self.threshold

    def _describe_anomaly(
        self,
        current: float,
        history: list[float],
        score: float,
    ) -> str:
        """生成异常描述"""
        mean = statistics.mean(history)
        ratio = current / mean if mean > 0 else 0
        return f"成交量突刺，为均值的 {ratio:.1f} 倍，异常分数 {score:.2f}"
