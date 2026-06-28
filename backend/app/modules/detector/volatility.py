"""
波动异常检测器。
基于百分位法检测日内振幅异常。
"""

import statistics
from typing import Optional

from app.modules.detector.base import BaseDetector, DetectionResult, Severity
from app.modules.config import DetectorConfig


class VolatilityDetector(BaseDetector):
    """波动异常检测器（百分位法）"""

    name = "volatility"

    def __init__(self, config: Optional[DetectorConfig] = None):
        super().__init__()
        self.config = config or DetectorConfig()
        self.percentile_high = self.config.volatility_percentile_high  # 95
        self.percentile_low = self.config.volatility_percentile_low   # 5
        self.lookback_days = self.config.volatility_lookback_days

    def detect(self, current: dict, history: list[dict]) -> DetectionResult:
        """
        检测波动异常。

        算法：百分位法
        1. 计算日内振幅 = (high - low) / close × 100%
        2. 计算近 N 天振幅的分布
        3. 当前振幅处于历史极端位置 → 异常
        """
        high = current.get("high")
        low = current.get("low")
        close = current.get("close")

        if None in (high, low, close) or close <= 0:
            return DetectionResult(
                detector_name=self.name,
                is_anomaly=False,
                severity=Severity.NORMAL,
                score=0.0,
                reason="无完整价格数据",
            )

        # 计算日内振幅
        amplitude = (high - low) / close * 100

        if len(history) < 10:
            return DetectionResult(
                detector_name=self.name,
                is_anomaly=False,
                severity=Severity.NORMAL,
                score=0.0,
                reason="历史数据不足",
            )

        # 计算历史振幅
        amplitudes = []
        for h in history:
            h_high = h.get("high")
            h_low = h.get("low")
            h_close = h.get("close")
            if None not in (h_high, h_low, h_close) and h_close > 0:
                amplitudes.append((h_high - h_low) / h_close * 100)

        if len(amplitudes) < 10:
            return DetectionResult(
                detector_name=self.name,
                is_anomaly=False,
                severity=Severity.NORMAL,
                score=0.0,
                reason="有效历史数据不足",
            )

        # 计算百分位阈值
        sorted_amps = sorted(amplitudes)
        p_low = self._percentile(sorted_amps, self.percentile_low)
        p_high = self._percentile(sorted_amps, self.percentile_high)
        mean_amp = statistics.mean(amplitudes)

        # 判断异常
        is_anomaly = amplitude < p_low or amplitude > p_high

        # 计算异常分数
        if is_anomaly:
            if amplitude > p_high:
                # 振幅过大
                ratio = amplitude / p_high
                score = min(1.0, 0.5 + 0.3 * (ratio - 1.0))
            else:
                # 振幅过小
                ratio = amplitude / p_low if p_low > 0 else 1.0
                score = min(0.8, 0.4 + 0.3 * (1.0 - ratio))
        else:
            score = 0.0

        # 判断严重程度
        if amplitude > p_high * 2 or (p_low > 0 and amplitude < p_low / 2):
            severity = Severity.CRITICAL
        elif amplitude > p_high * 1.5 or (p_low > 0 and amplitude < p_low * 0.7):
            severity = Severity.HIGH
        elif amplitude > p_high * 1.2 or (p_low > 0 and amplitude < p_low * 0.85):
            severity = Severity.MEDIUM
        elif is_anomaly:
            severity = Severity.LOW
        else:
            severity = Severity.NORMAL

        # 生成原因描述
        if amplitude > p_high:
            reason = f"日内振幅过大 {amplitude:.2f}%（超过 {self.percentile_high}% 分位 {p_high:.2f}%）"
        elif amplitude < p_low:
            reason = f"日内振幅过小 {amplitude:.2f}%（低于 {self.percentile_low}% 分位 {p_low:.2f}%）"
        else:
            reason = f"日内振幅正常 {amplitude:.2f}%"

        return DetectionResult(
            detector_name=self.name,
            is_anomaly=is_anomaly,
            severity=severity,
            score=score,
            reason=reason,
            details={
                "amplitude": round(amplitude, 2),
                "mean_amplitude": round(mean_amp, 2),
                "percentile_low": round(p_low, 2),
                "percentile_high": round(p_high, 2),
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
