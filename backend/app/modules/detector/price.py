"""
价格异常检测器。
基于 Z-Score 算法检测价格涨跌幅异常。
"""

import statistics
from typing import Optional

from app.modules.detector.base import BaseDetector, DetectionResult, Severity
from app.modules.config import DetectorConfig


class PriceDetector(BaseDetector):
    """价格异常检测器（Z-Score）"""

    name = "price"

    def __init__(self, config: Optional[DetectorConfig] = None):
        super().__init__()
        self.config = config or DetectorConfig()
        self.threshold = self.config.zscore_threshold
        self.lookback_days = self.config.zscore_lookback_days

    def detect(self, current: dict, history: list[dict]) -> DetectionResult:
        """
        检测价格异常。

        算法：Z-Score（3σ原则）
        1. 计算近 N 天涨跌幅的均值 μ 和标准差 σ
        2. 当前涨跌幅 z = (当前值 - μ) / σ
        3. |z| > threshold → 异常
        """
        change_pct = current.get("change_pct")

        if change_pct is None:
            return DetectionResult(
                detector_name=self.name,
                is_anomaly=False,
                severity=Severity.NORMAL,
                score=0.0,
                reason="无涨跌幅数据",
            )

        if len(history) < 5:
            return DetectionResult(
                detector_name=self.name,
                is_anomaly=False,
                severity=Severity.NORMAL,
                score=0.0,
                reason="历史数据不足",
            )

        # 提取历史涨跌幅
        changes = [h.get("change_pct", 0) for h in history if h.get("change_pct") is not None]

        if len(changes) < 5:
            return DetectionResult(
                detector_name=self.name,
                is_anomaly=False,
                severity=Severity.NORMAL,
                score=0.0,
                reason="有效历史数据不足",
            )

        # 计算均值和标准差
        mean = statistics.mean(changes)
        stdev = statistics.stdev(changes)

        if stdev == 0:
            # 标准差为0，无法判断
            return DetectionResult(
                detector_name=self.name,
                is_anomaly=False,
                severity=Severity.NORMAL,
                score=0.0,
                reason="历史波动率为0",
            )

        # 计算 Z-Score
        z_score = (change_pct - mean) / stdev
        abs_z = abs(z_score)

        # 计算异常分数（0-1）
        if abs_z <= 1.0:
            score = 0.0
        elif abs_z <= 2.0:
            score = 0.3 + 0.2 * (abs_z - 1.0)
        elif abs_z <= 2.5:
            score = 0.5 + 0.2 * (abs_z - 2.0)
        elif abs_z <= 3.0:
            score = 0.7 + 0.15 * (abs_z - 2.5)
        else:
            score = min(1.0, 0.85 + 0.05 * (abs_z - 3.0))

        # 判断是否异常
        is_anomaly = abs_z > self.threshold

        # 判断严重程度
        if abs_z > 3.5:
            severity = Severity.CRITICAL
        elif abs_z > 3.0:
            severity = Severity.HIGH
        elif abs_z > 2.5:
            severity = Severity.MEDIUM
        elif abs_z > 2.0:
            severity = Severity.LOW
        else:
            severity = Severity.NORMAL
            is_anomaly = False

        # 生成原因描述
        direction = "上涨" if change_pct > 0 else "下跌"
        if is_anomaly:
            reason = f"涨跌幅偏离均值 {z_score:.1f} 个标准差（{direction} {change_pct:.2f}%）"
        else:
            reason = f"涨跌幅正常（{direction} {change_pct:.2f}%，偏离 {z_score:.1f}σ）"

        return DetectionResult(
            detector_name=self.name,
            is_anomaly=is_anomaly,
            severity=severity,
            score=score,
            reason=reason,
            details={
                "z_score": round(z_score, 2),
                "change_pct": change_pct,
                "mean": round(mean, 2),
                "stdev": round(stdev, 2),
            },
        )
