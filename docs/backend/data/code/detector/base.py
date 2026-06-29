"""基础检测器"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class AnomalyResult:
    """异常结果"""

    date: date
    value: float
    score: float  # 0-1，异常分数
    is_anomaly: bool
    type: str  # 异常类型
    threshold: float
    description: Optional[str] = None


@dataclass
class DetectionResult:
    """检测结果"""

    symbol: str
    start_date: date
    end_date: date
    anomalies: list[AnomalyResult]
    total_count: int
    anomaly_count: int

    @property
    def anomaly_rate(self) -> float:
        """异常率"""
        if self.total_count == 0:
            return 0.0
        return self.anomaly_count / self.total_count


class BaseDetector(ABC):
    """异常检测器基类"""

    def __init__(self, threshold: float = 0.8):
        """
        Args:
            threshold: 异常阈值，0-1，超过此值视为异常
        """
        self.threshold = threshold

    @abstractmethod
    def detect(
        self,
        values: list[float],
        dates: list[date],
    ) -> DetectionResult:
        """
        检测异常

        Args:
            values: 数值序列
            dates: 日期序列

        Returns:
            DetectionResult
        """
        pass

    def calculate_zscore(
        self,
        value: float,
        mean: float,
        std: float,
    ) -> float:
        """计算 Z-Score"""
        if std == 0:
            return 0.0
        return (value - mean) / std
