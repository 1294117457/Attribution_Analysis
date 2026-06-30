# Step 6: Detector 异常检测模块

> ⚠️ **TODO**: 此模块暂未实现，专注于数据采集模块。

---

## 1. 目录结构

```
backend/
├── detector/
│   ├── __init__.py
│   ├── base.py           # 基础检测器
│   ├── price_detector.py # 价格异常检测
│   ├── volume_detector.py # 成交量异常检测
│   └── service.py        # 检测服务
```

---

## 2. 计划实现

### 2.1 基础检测器 (detector/base.py)

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


class BaseDetector(ABC):
    """异常检测器基类"""

    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold

    @abstractmethod
    def detect(
        self,
        values: list[float],
        dates: list[date],
    ) -> list[AnomalyResult]:
        pass
```

### 2.2 价格异常检测器 (detector/price_detector.py)

```python
"""价格异常检测器"""

import statistics
from detector.base import BaseDetector, AnomalyResult


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
        super().__init__(threshold)
        self.method = method
        self.lookback = lookback

    def detect(
        self,
        values: list[float],
        dates: list[date],
    ) -> list[AnomalyResult]:
        """检测价格异常"""
        # TODO: 实现检测逻辑
        pass
```

---

## 3. 数据流向

```
AkShare 采集
    ↓
数据库存储 (stock_klines 表)
    ↓
Detector 读取 K 线数据
    ↓
异常检测 (价格/成交量/波动率)
    ↓
异常记录存储 (anomalies 表)
```

---

## 4. 相关资源

- [AkShare 文档](https://www.akshare.xyz/)
- [Pandas TA 库](https://github.com/twopirllc/pandas-ta) - 技术指标计算
