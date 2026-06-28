"""
趋势异常检测器。
基于均线、MACD、布林带检测趋势异常。
"""

from typing import Optional, Tuple

from app.modules.detector.base import BaseDetector, DetectionResult, Severity
from app.modules.config import DetectorConfig


class TrendDetector(BaseDetector):
    """趋势异常检测器"""

    name = "trend"

    def __init__(self, config: Optional[DetectorConfig] = None):
        super().__init__()
        self.config = config or DetectorConfig()
        self.ma_periods = self.config.ma_periods  # [5, 20, 60]
        self.boll_period = self.config.boll_period  # 20
        self.boll_std = self.config.boll_std       # 2.0

    def detect(self, current: dict, history: list[dict]) -> DetectionResult:
        """
        检测趋势异常。

        检测项：
        1. 均线死叉/金叉
        2. 跌破/突破重要均线
        3. 突破布林带上下轨
        """
        close = current.get("close")

        if close is None or close <= 0:
            return DetectionResult(
                detector_name=self.name,
                is_anomaly=False,
                severity=Severity.NORMAL,
                score=0.0,
                reason="无收盘价数据",
            )

        if len(history) < max(self.ma_periods) + 1:
            return DetectionResult(
                detector_name=self.name,
                is_anomaly=False,
                severity=Severity.NORMAL,
                score=0.0,
                reason="历史数据不足",
            )

        # 计算技术指标
        closes = [h.get("close", 0) for h in reversed(history + [current])]
        highs = [h.get("high", 0) for h in reversed(history + [current])]
        lows = [h.get("low", 0) for h in reversed(history + [current])]

        ma_values = self._calculate_ma(closes)
        boll_values = self._calculate_boll(closes)
        prev_ma_values = self._calculate_ma(closes[:-1])  # 前一天

        anomalies = []
        max_severity = Severity.NORMAL
        total_score = 0.0

        # 1. 均线死叉/金叉检测
        ma_cross = self._detect_ma_cross(ma_values, prev_ma_values)
        if ma_cross:
            anomalies.append(ma_cross)
            total_score += 0.25

        # 2. 跌破/突破均线检测
        ma_breach = self._detect_ma_breach(close, ma_values)
        if ma_breach:
            anomalies.append(ma_breach)
            total_score += 0.2

        # 3. 布林带检测
        boll_breach = self._detect_boll_breach(close, boll_values)
        if boll_breach:
            anomalies.append(boll_breach)
            total_score += 0.25

        # 4. 涨跌停检测
        change_pct = current.get("change_pct")
        limit_hit = self._detect_limit_hit(change_pct)
        if limit_hit:
            anomalies.append(limit_hit)
            total_score += 0.3

        # 判断是否有异常
        is_anomaly = len(anomalies) > 0

        if is_anomaly:
            # 取最高严重程度
            severity_scores = {
                Severity.CRITICAL: 4,
                Severity.HIGH: 3,
                Severity.MEDIUM: 2,
                Severity.LOW: 1,
                Severity.NORMAL: 0,
            }
            max_severity = max((a["severity"] for a in anomalies), key=lambda s: severity_scores.get(s, 0))
            max_severity = Severity(max_severity.value if hasattr(max_severity, "value") else max_severity)

            # 限制分数范围
            total_score = min(1.0, total_score)

        # 生成原因描述
        if anomalies:
            reason = "；".join(a["reason"] for a in anomalies)
        else:
            reason = "趋势正常"

        return DetectionResult(
            detector_name=self.name,
            is_anomaly=is_anomaly,
            severity=max_severity,
            score=total_score,
            reason=reason,
            details={
                "anomalies": anomalies,
                "ma_values": {f"ma{p}": round(v, 2) for p, v in zip(self.ma_periods, ma_values[-3:]) if v},
                "boll_upper": round(boll_values["upper"], 2) if boll_values else None,
                "boll_lower": round(boll_values["lower"], 2) if boll_values else None,
            },
        )

    def _calculate_ma(self, closes: list[float]) -> dict[int, list[float]]:
        """计算移动平均线"""
        ma_values = {}
        for period in self.ma_periods:
            ma_values[period] = []
            for i in range(len(closes)):
                if i < period - 1:
                    ma_values[period].append(None)
                else:
                    ma = sum(closes[i - period + 1:i + 1]) / period
                    ma_values[period].append(ma)
        return ma_values

    def _calculate_boll(self, closes: list[float]) -> dict[str, float]:
        """计算布林带（仅最新值）"""
        if len(closes) < self.boll_period:
            return {}

        period_closes = closes[-self.boll_period:]
        ma = sum(period_closes) / self.boll_period

        # 计算标准差
        variance = sum((c - ma) ** 2 for c in period_closes) / self.boll_period
        std = variance ** 0.5

        return {
            "middle": ma,
            "upper": ma + self.boll_std * std,
            "lower": ma - self.boll_std * std,
        }

    def _detect_ma_cross(
        self, ma_values: dict[int, list[float]], prev_ma_values: dict[int, list[float]]
    ) -> Optional[dict]:
        """检测均线交叉"""
        if len(self.ma_periods) < 2:
            return None

        ma5 = self.ma_periods[0]   # 5
        ma20 = self.ma_periods[1]  # 20

        current_ma5 = ma_values.get(ma5, [None])[-1]
        current_ma20 = ma_values.get(ma20, [None])[-1]
        prev_ma5 = prev_ma_values.get(ma5, [None])[-1]
        prev_ma20 = prev_ma_values.get(ma20, [None])[-1]

        if None in (current_ma5, current_ma20, prev_ma5, prev_ma20):
            return None

        # 死叉：MA5 下穿 MA20（多头转空头）
        if prev_ma5 >= prev_ma20 and current_ma5 < current_ma20:
            return {
                "type": "death_cross",
                "severity": Severity.HIGH,
                "reason": f"均线死叉（MA5={current_ma5:.2f}下穿MA20={current_ma20:.2f}）",
            }

        # 金叉：MA5 上穿 MA20（空头转多头）
        if prev_ma5 <= prev_ma20 and current_ma5 > current_ma20:
            return {
                "type": "golden_cross",
                "severity": Severity.HIGH,
                "reason": f"均线金叉（MA5={current_ma5:.2f}上穿MA20={current_ma20:.2f}）",
            }

        return None

    def _detect_ma_breach(self, close: float, ma_values: dict[int, list[float]]) -> Optional[dict]:
        """检测跌破/突破均线"""
        anomalies = []

        for period in self.ma_periods:
            if period == 60:  # 只检测 MA20
                continue
            ma = ma_values.get(period, [None])[-1]
            if ma is None:
                continue

            if close < ma * 0.95:
                anomalies.append({
                    "type": "below_ma",
                    "period": period,
                    "reason": f"跌破MA{period}（{close:.2f}<{ma:.2f}）",
                    "severity": Severity.MEDIUM if period == 20 else Severity.LOW,
                })
            elif close > ma * 1.05:
                anomalies.append({
                    "type": "above_ma",
                    "period": period,
                    "reason": f"突破MA{period}（{close:.2f}>{ma:.2f}）",
                    "severity": Severity.MEDIUM if period == 20 else Severity.LOW,
                })

        if anomalies:
            # 返回最严重的
            return max(anomalies, key=lambda a: 3 if a["severity"] == Severity.MEDIUM else 1)
        return None

    def _detect_boll_breach(self, close: float, boll_values: dict[str, float]) -> Optional[dict]:
        """检测突破布林带"""
        if not boll_values:
            return None

        upper = boll_values.get("upper", 0)
        lower = boll_values.get("lower", 0)

        if close > upper:
            return {
                "type": "break_upper",
                "severity": Severity.HIGH,
                "reason": f"突破布林上轨（{close:.2f}>{upper:.2f}）",
            }
        elif close < lower:
            return {
                "type": "break_lower",
                "severity": Severity.HIGH,
                "reason": f"跌破布林下轨（{close:.2f}<{lower:.2f}）",
            }

        return None

    def _detect_limit_hit(self, change_pct: Optional[float]) -> Optional[dict]:
        """检测涨跌停"""
        if change_pct is None:
            return None

        if change_pct >= 9.9:  # 接近涨停
            return {
                "type": "limit_up",
                "severity": Severity.CRITICAL,
                "reason": f"触及涨停（涨跌幅 {change_pct:.2f}%）",
            }
        elif change_pct <= -9.9:  # 接近跌停
            return {
                "type": "limit_down",
                "severity": Severity.CRITICAL,
                "reason": f"触及跌停（涨跌幅 {change_pct:.2f}%）",
            }

        return None
