# 异常检测模块开发步骤

## 概述

异常检测是数据采集后的第一层分析，检测股票价格/成交量中的异常波动。

---

## 开发步骤

### Step 1: 创建目录结构

```
backend/ml/
├── __init__.py
├── config.py
│
├── models/                    # ML 模型定义
│   ├── __init__.py
│   ├── anomaly.py            # 异常检测相关模型
│   └── feature.py           # 特征模型
│
├── detector/                  # 异常检测器
│   ├── __init__.py
│   ├── base.py              # BaseDetector
│   ├── zscore_detector.py   # Z-Score 检测
│   ├── iqr_detector.py     # IQR 检测
│   └── volatility_detector.py # 波动率检测
│
├── features/                  # 特征工程
│   ├── __init__.py
│   ├── technical.py         # 技术指标
│   └── statistical.py       # 统计特征
│
└── scripts/                  # ML 脚本
    ├── __init__.py
    └── evaluate_detector.py  # 评估检测器
```

### Step 2: 异常检测模型 (`models/anomaly.py`)

```python
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional
from enum import Enum

class DetectorType(str, Enum):
    """检测器类型"""
    ZSCORE = "zscore"
    IQR = "iqr"
    VOLATILITY = "volatility"
    ISOLATION_FOREST = "isolation_forest"

class AnomalyScore(BaseModel):
    """异常分数"""
    date: date
    value: float
    score: float = Field(..., ge=0, le=1, description="异常分数，0-1")
    is_anomaly: bool = Field(..., description="是否异常")
    threshold: float
    details: Optional[dict] = None

class DetectionConfig(BaseModel):
    """检测配置"""
    detector_type: DetectorType
    threshold: float = Field(0.95, description="异常阈值 (0-1)")
    lookback_period: int = Field(30, description="回看周期")

class DetectionResult(BaseModel):
    """检测结果"""
    symbol: str
    detector_type: DetectorType
    start_date: date
    end_date: date
    scores: list[AnomalyScore]
    anomaly_count: int
    anomaly_dates: list[date]

    @property
    def anomaly_rate(self) -> float:
        """异常率"""
        if not self.scores:
            return 0.0
        return self.anomaly_count / len(self.scores)
```

### Step 3: 特征模型 (`models/feature.py`)

```python
from pydantic import BaseModel
from datetime import date

class PriceFeature(BaseModel):
    """价格特征"""
    date: date
    close: float
    change_pct: float
    volume: float
    amount: float

    # 统计特征
    mean: float
    std: float
    z_score: float

    # 历史特征
    returns_1d: float
    returns_5d: float
    returns_20d: float
```

### Step 4: 基础检测器 (`detector/base.py`)

```python
from abc import ABC, abstractmethod
from datetime import date
from ml.models.anomaly import DetectionConfig, DetectionResult, AnomalyScore

class BaseDetector(ABC):
    """异常检测器基类"""

    def __init__(self, config: DetectionConfig):
        self.config = config

    @abstractmethod
    def detect(self, prices: list[float], dates: list[date]) -> DetectionResult:
        """
        检测异常

        Args:
            prices: 价格序列
            dates: 日期序列

        Returns:
            DetectionResult
        """
        pass

    def _create_score(
        self,
        date: date,
        value: float,
        score: float,
    ) -> AnomalyScore:
        """创建异常分数"""
        return AnomalyScore(
            date=date,
            value=value,
            score=score,
            is_anomaly=score >= self.config.threshold,
            threshold=self.config.threshold,
        )
```

### Step 5: Z-Score 检测器 (`detector/zscore_detector.py`)

```python
import statistics
import math
from datetime import date
from typing import Optional
from ml.detector.base import BaseDetector
from ml.models.anomaly import (
    DetectionConfig,
    DetectionResult,
    AnomalyScore,
    DetectorType,
)

class ZScoreDetector(BaseDetector):
    """Z-Score 异常检测器

    原理：
    - 计算历史均值和标准差
    - Z = (x - μ) / σ
    - |Z| > 2 通常视为异常
    """

    def detect(
        self,
        prices: list[float],
        dates: list[date],
    ) -> DetectionResult:
        """检测价格异常"""
        if len(prices) < self.config.lookback_period:
            raise ValueError(f"数据量不足，需要至少 {self.config.lookback_period} 个数据点")

        # 计算历史均值和标准差
        lookback_prices = prices[:-1]  # 不包含当前点
        mean = statistics.mean(lookback_prices)
        std = statistics.stdev(lookback_prices) if len(lookback_prices) > 1 else 0

        if std == 0:
            std = 1e-8  # 避免除零

        scores = []
        anomaly_dates = []

        for i, (price, d) in enumerate(zip(prices, dates)):
            # 计算 Z-Score
            z_score = (price - mean) / std

            # 转换为 0-1 分数（使用 sigmoid）
            score = self._z_to_score(z_score)

            anomaly_score = self._create_score(d, price, score)
            scores.append(anomaly_score)

            if anomaly_score.is_anomaly:
                anomaly_dates.append(d)

        return DetectionResult(
            symbol="",  # 由调用方设置
            detector_type=DetectorType.ZSCORE,
            start_date=dates[0],
            end_date=dates[-1],
            scores=scores,
            anomaly_count=len(anomaly_dates),
            anomaly_dates=anomaly_dates,
        )

    def _z_to_score(self, z: float) -> float:
        """Z-Score 转 0-1 分数（使用双侧 sigmoid）"""
        # |Z| 越大，分数越高
        abs_z = abs(z)
        # sigmoid: 1 / (1 + e^(-k*(|z|-threshold)))
        k = 1.0
        threshold_z = 2.0  # |Z| > 2 视为异常
        score = 1 / (1 + math.exp(-k * (abs_z - threshold_z)))
        return score
```

### Step 6: IQR 检测器 (`detector/iqr_detector.py`)

```python
import statistics
from datetime import date
from ml.detector.base import BaseDetector
from ml.models.anomaly import (
    DetectionConfig,
    DetectionResult,
    DetectorType,
)

class IQRDetector(BaseDetector):
    """IQR 四分位距异常检测器

    原理：
    - Q1 = 25% 分位数
    - Q3 = 75% 分位数
    - IQR = Q3 - Q1
    - 异常：value < Q1 - 1.5*IQR 或 value > Q3 + 1.5*IQR
    """

    def detect(
        self,
        prices: list[float],
        dates: list[date],
    ) -> DetectionResult:
        """检测价格异常"""
        if len(prices) < 10:
            raise ValueError("IQR 检测需要至少 10 个数据点")

        lookback_prices = prices[:-1]

        # 计算分位数
        q1 = statistics.quantiles(lookback_prices, n=4)[0]
        q3 = statistics.quantiles(lookback_prices, n=4)[2]
        iqr = q3 - q1

        # 计算边界
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        scores = []
        anomaly_dates = []

        for price, d in zip(prices, dates):
            # 计算分数：超出边界越多，分数越高
            if price < lower_bound:
                distance = lower_bound - price
                score = min(distance / iqr, 1.0) if iqr > 0 else 1.0
            elif price > upper_bound:
                distance = price - upper_bound
                score = min(distance / iqr, 1.0) if iqr > 0 else 1.0
            else:
                # 在正常范围内，距离边界越近分数越高
                mid = (lower_bound + upper_bound) / 2
                range_half = (upper_bound - lower_bound) / 2
                normalized = abs(price - mid) / range_half
                score = normalized * 0.5  # 最高 0.5

            anomaly_score = self._create_score(d, price, score)
            scores.append(anomaly_score)

            if anomaly_score.is_anomaly:
                anomaly_dates.append(d)

        return DetectionResult(
            symbol="",
            detector_type=DetectorType.IQR,
            start_date=dates[0],
            end_date=dates[-1],
            scores=scores,
            anomaly_count=len(anomaly_dates),
            anomaly_dates=anomaly_dates,
        )
```

### Step 7: 波动率检测器 (`detector/volatility_detector.py`)

```python
import math
import statistics
from datetime import date
from ml.detector.base import BaseDetector
from ml.models.anomaly import (
    DetectionConfig,
    DetectionResult,
    DetectorType,
)

class VolatilityDetector(BaseDetector):
    """波动率异常检测器

    原理：
    - 计算历史收益率的标准差
    - 当前波动率超过历史均值 + N*标准差 视为异常
    """

    def detect(
        self,
        prices: list[float],
        dates: list[date],
    ) -> DetectionResult:
        """检测波动率异常"""
        if len(prices) < self.config.lookback_period + 1:
            raise ValueError(f"需要至少 {self.config.lookback_period + 1} 个数据点")

        # 计算收益率
        returns = []
        for i in range(1, len(prices)):
            ret = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append(ret)

        # 历史波动率统计
        lookback_returns = returns[:-1]
        hist_mean = statistics.mean(lookback_returns)
        hist_std = statistics.stdev(lookback_returns) if len(lookback_returns) > 1 else 0

        if hist_std == 0:
            hist_std = 1e-8

        scores = []
        anomaly_dates = []

        for i, (ret, d) in enumerate(zip(returns, dates[1:])):
            # 当前波动率偏离历史均值
            z = abs(ret - hist_mean) / hist_std
            score = 1 / (1 + math.exp(-(z - 2)))  # Z > 2 视为异常

            anomaly_score = self._create_score(d, ret, score)
            scores.append(anomaly_score)

            if anomaly_score.is_anomaly:
                anomaly_dates.append(d)

        return DetectionResult(
            symbol="",
            detector_type=DetectorType.VOLATILITY,
            start_date=dates[0],
            end_date=dates[-1],
            scores=scores,
            anomaly_count=len(anomaly_dates),
            anomaly_dates=anomaly_dates,
        )
```

### Step 8: 特征计算 (`features/statistical.py`)

```python
import statistics
import math
from datetime import date
from core.models.stock import StockKline

class StatisticalFeatures:
    """统计特征计算"""

    @staticmethod
    def calculate_zscore(
        value: float,
        history: list[float],
    ) -> float:
        """计算 Z-Score"""
        if len(history) < 2:
            return 0.0
        mean = statistics.mean(history)
        std = statistics.stdev(history)
        if std == 0:
            return 0.0
        return (value - mean) / std

    @staticmethod
    def calculate_returns(
        prices: list[float],
    ) -> list[float]:
        """计算收益率序列"""
        returns = []
        for i in range(1, len(prices)):
            ret = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append(ret)
        return returns

    @staticmethod
    def calculate_volatility(
        returns: list[float],
        window: int = 20,
    ) -> float:
        """计算波动率（年化）"""
        if len(returns) < window:
            return 0.0
        recent_returns = returns[-window:]
        std = statistics.stdev(recent_returns)
        # 年化（252 交易日）
        return std * math.sqrt(252)
```

### Step 9: 评估脚本 (`scripts/evaluate_detector.py`)

```python
"""
评估异常检测器
使用方法: python -m ml.scripts.evaluate_detector
"""

from datetime import date, timedelta
import asyncio
from ml.detector.zscore_detector import ZScoreDetector
from ml.detector.iqr_detector import IQRDetector
from ml.detector.volatility_detector import VolatilityDetector
from ml.models.anomaly import DetectionConfig, DetectorType
from data.collectors.stock_collector import StockCollector

async def evaluate():
    """评估检测器"""
    # 采集数据
    collector = StockCollector()
    symbol = "000001"
    end_date = date.today()
    start_date = end_date - timedelta(days=365)

    result = await collector.collect(symbol, start_date, end_date)
    if result.status != "success":
        print("采集失败")
        return

    # 准备数据
    # TODO: 从数据库或采集结果获取价格序列
    prices = [100.0] * 100  # 模拟数据
    dates = [end_date - timedelta(days=99-i) for i in range(100)]

    # 配置
    config = DetectionConfig(
        detector_type=DetectorType.ZSCORE,
        threshold=0.8,
        lookback_period=30,
    )

    # 测试检测器
    detectors = [
        ("Z-Score", ZScoreDetector(config)),
        ("IQR", IQRDetector(config)),
        ("Volatility", VolatilityDetector(config)),
    ]

    for name, detector in detectors:
        print(f"\n=== {name} 检测器 ===")
        result = detector.detect(prices, dates)
        print(f"异常数: {result.anomaly_count}")
        print(f"异常率: {result.anomaly_rate:.2%}")
        print(f"异常日期: {result.anomaly_dates[:5]}")

if __name__ == "__main__":
    asyncio.run(evaluate())
```

---

## 验证清单

- [ ] ZScoreDetector 能正确检测价格异常
- [ ] IQRDetector 能正确检测价格异常
- [ ] VolatilityDetector 能正确检测波动率异常
- [ ] 检测结果格式正确
- [ ] 异常分数在 0-1 范围内
- [ ] 评估脚本能运行

---

## 目录结构汇总

```
ml/
├── __init__.py
├── config.py
│
├── models/
│   ├── __init__.py
│   ├── anomaly.py
│   └── feature.py
│
├── detector/
│   ├── __init__.py
│   ├── base.py
│   ├── zscore_detector.py
│   ├── iqr_detector.py
│   └── volatility_detector.py
│
├── features/
│   ├── __init__.py
│   └── statistical.py
│
└── scripts/
    ├── __init__.py
    └── evaluate_detector.py
```
