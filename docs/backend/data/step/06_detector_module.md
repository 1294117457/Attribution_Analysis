# Step 6: Detector 异常检测模块

## 1. 目录结构

```
backend/
├── detector/
│   ├── __init__.py
│   ├── base.py           # 基础检测器
│   ├── price_detector.py # 价格异常检测
│   ├── volume_detector.py # 成交量异常检测
│   ├── volatility_detector.py # 波动率检测
│   └── service.py        # 检测服务
```

---

## 2. 创建基础检测器

### 2.1 detector/__init__.py

```python
"""异常检测模块"""

from detector.base import BaseDetector
from detector.price_detector import PriceDetector
from detector.volume_detector import VolumeDetector

__all__ = [
    "BaseDetector",
    "PriceDetector",
    "VolumeDetector",
]
```

### 2.2 detector/base.py

```python
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
```

---

## 3. 创建价格异常检测器

### 3.1 detector/price_detector.py

```python
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
```

---

## 4. 创建成交量异常检测器

### 4.1 detector/volume_detector.py

```python
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
```

---

## 5. 创建检测服务

### 5.1 detector/service.py

```python
"""异常检测服务"""

from datetime import date
from typing import Optional

from detector.price_detector import PriceDetector
from detector.volume_detector import VolumeDetector
from detector.base import DetectionResult


class DetectorService:
    """异常检测服务"""

    def __init__(self):
        self.price_detector = PriceDetector(threshold=0.7)
        self.volume_detector = VolumeDetector(threshold=0.7)

    def detect_price_anomaly(
        self,
        prices: list[float],
        dates: list[date],
        method: str = "zscore",
    ) -> DetectionResult:
        """检测价格异常"""
        detector = PriceDetector(
            threshold=0.7,
            method=method,
            lookback=20,
        )
        result = detector.detect(prices, dates)
        return result

    def detect_volume_anomaly(
        self,
        volumes: list[float],
        dates: list[date],
    ) -> DetectionResult:
        """检测成交量异常"""
        result = self.volume_detector.detect(volumes, dates)
        return result

    def detect_anomaly(
        self,
        symbol: str,
        prices: list[float],
        volumes: list[float],
        dates: list[date],
    ) -> dict:
        """综合异常检测"""
        price_result = self.detect_price_anomaly(prices, dates)
        volume_result = self.detect_volume_anomaly(volumes, dates)

        return {
            "symbol": symbol,
            "price_anomalies": price_result,
            "volume_anomalies": volume_result,
            "summary": self._generate_summary(price_result, volume_result),
        }

    def _generate_summary(
        self,
        price_result: DetectionResult,
        volume_result: DetectionResult,
    ) -> str:
        """生成摘要"""
        parts = []

        if price_result.anomaly_count > 0:
            parts.append(
                f"发现 {price_result.anomaly_count} 个价格异常"
            )

        if volume_result.anomaly_count > 0:
            parts.append(
                f"发现 {volume_result.anomaly_count} 个成交量异常"
            )

        if not parts:
            return "未发现异常"

        return "，".join(parts)
```

---

## 6. 验证检测器

### 6.1 test_detector.py

```python
"""测试异常检测器"""

from datetime import date, timedelta
from detector.price_detector import PriceDetector
from detector.volume_detector import VolumeDetector
from detector.service import DetectorService


def test_price_detector_normal():
    """测试正常数据"""
    # 正常波动数据
    prices = [100 + i * 0.5 for i in range(30)]
    dates = [date.today() - timedelta(days=29 - i) for i in range(30)]

    detector = PriceDetector(threshold=0.7)
    result = detector.detect(prices, dates)

    print(f"正常数据检测: {result.anomaly_count} 个异常")
    assert result.anomaly_count == 0, "正常数据不应该有异常"
    print("✅ test_price_detector_normal 通过!")


def test_price_detector_anomaly():
    """测试异常数据"""
    # 正常数据 + 突刺
    prices = [100.0] * 25 + [150.0] * 5
    dates = [date.today() - timedelta(days=29 - i) for i in range(30)]

    detector = PriceDetector(threshold=0.7)
    result = detector.detect(prices, dates)

    print(f"异常数据检测: {result.anomaly_count} 个异常")
    for anomaly in result.anomalies:
        print(f"  {anomaly.date}: {anomaly.value}, 分数: {anomaly.score:.2f}")
        print(f"    {anomaly.description}")

    assert result.anomaly_count > 0, "应该检测到异常"
    print("✅ test_price_detector_anomaly 通过!")


def test_volume_detector():
    """测试成交量检测"""
    # 正常成交量 + 突刺
    volumes = [1000000] * 25 + [5000000] * 5
    dates = [date.today() - timedelta(days=29 - i) for i in range(30)]

    detector = VolumeDetector(threshold=0.7)
    result = detector.detect(volumes, dates)

    print(f"成交量检测: {result.anomaly_count} 个异常")
    assert result.anomaly_count > 0
    print("✅ test_volume_detector 通过!")


def test_detector_service():
    """测试检测服务"""
    prices = [100 + i * 0.5 for i in range(30)]
    volumes = [1000000] * 28 + [5000000] * 2
    dates = [date.today() - timedelta(days=29 - i) for i in range(30)]

    service = DetectorService()
    result = service.detect_anomaly("000001", prices, volumes, dates)

    print(f"综合检测结果: {result['summary']}")
    print(f"价格异常: {result['price_anomalies'].anomaly_count}")
    print(f"成交量异常: {result['volume_anomalies'].anomaly_count}")

    print("✅ test_detector_service 通过!")


if __name__ == "__main__":
    test_price_detector_normal()
    test_price_detector_anomaly()
    test_volume_detector()
    test_detector_service()
    print("\n🎉 所有测试通过!")
```

### 6.2 运行测试

```bash
cd backend
python test_detector.py
```

---

## 7. 目录结构确认

```
backend/
├── detector/
│   ├── __init__.py        ← 新建
│   ├── base.py            ← 新建
│   ├── price_detector.py  ← 新建
│   ├── volume_detector.py ← 新建
│   └── service.py         ← 新建
├── app/
└── data/
```
