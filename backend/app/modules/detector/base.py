"""
异常检测基类。
定义检测器接口和通用数据结构。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    """异常严重程度"""
    NORMAL = "normal"    # 正常
    LOW = "low"          # 低风险
    MEDIUM = "medium"    # 中风险
    HIGH = "high"        # 高风险
    CRITICAL = "critical"  # 极端


@dataclass
class DetectionResult:
    """单条检测结果"""
    detector_name: str                    # 检测器名称
    is_anomaly: bool = False              # 是否异常
    severity: Severity = Severity.NORMAL  # 严重程度
    score: float = 0.0                   # 异常分数 0-1
    reason: str = ""                     # 原因描述
    details: dict = field(default_factory=dict)  # 详细数据


class BaseDetector(ABC):
    """检测器基类"""

    name: str = "base"

    def __init__(self):
        self.results: list[DetectionResult] = []

    @abstractmethod
    def detect(self, current: dict, history: list[dict]) -> DetectionResult:
        """
        检测单条数据。

        Args:
            current: 当前 K 线数据
            history: 历史 K 线数据（用于计算基准）

        Returns:
            DetectionResult: 检测结果
        """
        raise NotImplementedError

    def detect_batch(self, klines: list[dict]) -> list[DetectionResult]:
        """
        批量检测多条 K 线。

        Args:
            klines: K 线数据列表（按日期升序）

        Returns:
            list[DetectionResult]: 检测结果列表
        """
        results = []

        for i in range(len(klines)):
            current = klines[i]
            # 取当前之前的历史数据
            history = klines[max(0, i - 30):i]
            result = self.detect(current, history)
            results.append(result)

        return results

    def get_result(self, current: dict, history: list[dict]) -> DetectionResult:
        """便捷方法：检测并返回结果"""
        return self.detect(current, history)
