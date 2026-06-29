"""价格异常检测器"""

import statistics
from datetime import date
from typing import Optional

from detector.base import BaseDetector, AnomalyResult, DetectionResult


class PriceDetector(BaseDetector):
    """
    价格异常检测器

    支持多种检测方法：
    1. zscore: Z-Score 检测（偏离均值 N 个标准差）
    2. iqr: IQR 四分位距检测
    3. change: 涨跌幅检测
    """

    def __init__(
        self,
        threshold: float = 0.8,
        method: str = "zscore",
        lookback: int = 20,
    ):
        """
        Args:
            threshold: 异常阈值
            method: 检测方法，"zscore", "iqr", "change"
            lookback: 回看周期
        """
        super().__init__(threshold)
        self.method = method
        self.lookback = lookback

    def detect(
        self,
        values: list[float],
        dates: list[date],
    ) -> DetectionResult:
        """检测价格异常"""
        if len(values) < self.lookback:
            raise ValueError(f"数据量不足，需要至少 {self.lookback} 个数据点")

        anomalies = []
        total_count = len(values)

        for i in range(self.lookback, total_count):
            # 历史数据（不包含当前点）
            history = values[i - self.lookback : i]
            current = values[i]
            current_date = dates[i]

            # 计算异常分数
            score, is_anomaly = self._detect_point(current, history)

            if is_anomaly:
                result = AnomalyResult(
                    date=current_date,
                    value=current,
                    score=score,
                    is_anomaly=True,
                    type="price_anomaly",
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
        if self.method == "zscore":
            return self._detect_zscore(current, history)
        elif self.method == "iqr":
            return self._detect_iqr(current, history)
        elif self.method == "change":
            return self._detect_change(current, history)
        else:
            return self._detect_zscore(current, history)

    def _detect_zscore(
        self,
        current: float,
        history: list[float],
    ) -> tuple[float, bool]:
        """Z-Score 检测"""
        mean = statistics.mean(history)
        std = statistics.stdev(history) if len(history) > 1 else 0

        if std == 0:
            return 0.0, False

        zscore = abs(current - mean) / std

        # 将 Z-Score 转换为 0-1 分数
        # Z=0 → 0, Z=2 → 0.5, Z=4 → 0.98
        score = 1 / (1 + (2 - zscore) ** 2) if zscore >= 0 else 0
        score = min(max(score, 0), 1)

        return score, score >= self.threshold

    def _detect_iqr(
        self,
        current: float,
        history: list[float],
    ) -> tuple[float, bool]:
        """IQR 四分位距检测"""
        sorted_data = sorted(history)
        n = len(sorted_data)

        # 计算四分位数
        q1_idx = n // 4
        q3_idx = 3 * n // 4
        q1 = sorted_data[q1_idx]
        q3 = sorted_data[q3_idx]
        iqr = q3 - q1

        # 计算边界
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        # 计算分数
        if current < lower:
            distance = lower - current
            score = min(distance / iqr, 1.0) if iqr > 0 else 1.0
        elif current > upper:
            distance = current - upper
            score = min(distance / iqr, 1.0) if iqr > 0 else 1.0
        else:
            score = 0.0

        return score, score >= self.threshold

    def _detect_change(
        self,
        current: float,
        history: list[float],
    ) -> tuple[float, bool]:
        """涨跌幅检测"""
        if len(history) < 2:
            return 0.0, False

        prev = history[-1]
        if prev == 0:
            return 0.0, False

        change_pct = abs(current - prev) / prev

        # 超过 5% 视为异常
        threshold_change = 0.05
        score = min(change_pct / threshold_change, 1.0)

        return score, score >= self.threshold

    def _describe_anomaly(
        self,
        current: float,
        history: list[float],
        score: float,
    ) -> str:
        """生成异常描述"""
        mean = statistics.mean(history)
        change = (current - mean) / mean * 100 if mean != 0 else 0

        direction = "上涨" if current > mean else "下跌"
        return f"价格{direction} {change:.2f}%，异常分数 {score:.2f}"
