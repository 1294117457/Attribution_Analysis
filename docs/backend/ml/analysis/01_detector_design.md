# 异常检测模块设计分析

## 1. 模块定位

```
┌─────────────────────────────────────────────────────────────────┐
│                      data/ (数据采集层)                          │
│   采集原始 K 线数据                                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       ml/detector/ (异常检测层)                   │
│                                                                 │
│   BaseDetector ──────▶ 检测器基类                                │
│   ZScoreDetector ────▶ Z-Score 检测                            │
│   IQRDetector ───────▶ IQR 四分位检测                          │
│   VolatilityDetector ▶ 波动率检测                               │
│   IsolationForest ──▶ 隔离森林检测 (后续扩展)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       app/ (API 层)                             │
│   存储异常记录，提供查询接口                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    graph/ (编排层)                               │
│   基于检测结果进行下一步分析                                     │
└─────────────────────────────────────────────────────────────────┘
```

## 2. 检测器设计

### 2.1 基类设计

```python
class BaseDetector(ABC):
    def __init__(self, config: DetectionConfig):
        self.config = config

    @abstractmethod
    def detect(
        self,
        prices: list[float],
        dates: list[date],
    ) -> DetectionResult:
        pass
```

**设计理由**：
- 抽象基类定义统一接口
- 配置对象注入，便于调整参数
- 返回统一的结果类型

### 2.2 检测器对比

| 检测器 | 原理 | 优点 | 缺点 | 适用场景 |
|--------|------|------|------|----------|
| Z-Score | 偏离均值 N 个标准差 | 简单、快速 | 对极端值敏感 | 正常分布数据 |
| IQR | 四分位距边界 | 鲁棒性强 | 敏感性较低 | 非正态分布 |
| Volatility | 收益率波动 | 捕捉波动异常 | 需要较长历史 | 极端行情 |

### 2.3 分数归一化

所有检测器的分数都归一化到 0-1：

```python
# 策略：使用 Sigmoid 函数
def _z_to_score(self, z: float) -> float:
    """
    Z-Score 越极端，分数越高
    - |Z| = 0 → score ≈ 0
    - |Z| = 2 → score ≈ 0.5
    - |Z| = 4 → score ≈ 0.98
    """
    k = 1.0
    threshold = 2.0
    return 1 / (1 + math.exp(-k * (abs(z) - threshold)))
```

**分数含义**：
| 分数范围 | 含义 | 建议动作 |
|----------|------|----------|
| 0.0 - 0.3 | 正常 | 不处理 |
| 0.3 - 0.7 | 可疑 | 关注 |
| 0.7 - 1.0 | 异常 | 告警 |

## 3. 配置设计

### 3.1 DetectionConfig

```python
class DetectionConfig(BaseModel):
    detector_type: DetectorType  # 检测器类型
    threshold: float = 0.95     # 异常阈值
    lookback_period: int = 30   # 回看周期
```

**参数说明**：

| 参数 | 说明 | 建议值 |
|------|------|--------|
| threshold | 超过此分数视为异常 | 0.8-0.95 |
| lookback_period | 用多少历史数据计算基准 | 20-60 天 |

### 3.2 阈值调优

```python
# 低敏感度（减少误报）
config = DetectionConfig(threshold=0.95, ...)

# 高敏感度（减少漏报）
config = DetectionConfig(threshold=0.70, ...)
```

## 4. 检测流程

### 4.1 完整流程

```
输入: 价格序列 [P1, P2, ..., Pn]
     日期序列 [D1, D2, ..., Dn]

Step 1: 计算基准
        历史数据 [P1, P2, ..., Pn-1]
        均值 μ, 标准差 σ

Step 2: 逐点检测
        for i in 1..n:
            计算 Z-Score: Zi = (Pi - μ) / σ
            计算分数: Scorei = sigmoid(|Zi|)

Step 3: 判断异常
        if Scorei >= threshold:
            标记为异常

输出: [Score1, Score2, ..., Scoren]
     异常日期列表
```

### 4.2 时序处理

```
prices:  [100, 102, 98,  105, 150, 152, 149, 151]
dates:   [d1,  d2,  d3,  d4,  d5,  d6,  d7,  d8]
scores:  [0.1, 0.2, 0.3, 0.5, 0.95, 0.8, 0.7, 0.6]
                            ▲
                         异常点
```

**注意**：
- 当前点的基准是用**历史数据**计算的
- 不包含当前点，避免前视偏差

## 5. 异常类型

### 5.1 涨幅异常

```python
# 检测涨幅异常
price = 150  # 当前价
prev_price = 105
change_pct = (price - prev_price) / prev_price * 100  # 42.86%
```

### 5.2 成交量异常

```python
# 类似价格检测，但输入为成交量序列
volumes = [1000000, 1100000, 950000, 1200000, 5000000, ...]
```

### 5.3 波动率异常

```python
# 检测日内波动异常
daily_volatility = (high - low) / close
```

## 6. 多检测器融合

### 6.1 投票机制

```python
def ensemble_detect(
    prices: list[float],
    dates: list[date],
    detectors: list[BaseDetector],
) -> DetectionResult:
    """多检测器投票"""
    all_scores = []
    anomaly_votes = []

    for detector in detectors:
        result = detector.detect(prices, dates)
        all_scores.append(result.scores)

    # 平均分数
    final_scores = []
    for i in range(len(prices)):
        avg_score = sum(s[i].score for s in all_scores) / len(all_scores)
        final_scores.append(AnomalyScore(
            date=dates[i],
            value=prices[i],
            score=avg_score,
            is_anomaly=avg_score >= 0.8,
            threshold=0.8,
        ))

    return DetectionResult(...)
```

### 6.2 评分矩阵

| 检测器 | 今日 | 昨日 | 前日 |
|--------|------|------|------|
| Z-Score | 0.95 ✓ | 0.3 | 0.2 |
| IQR | 0.85 ✓ | 0.4 | 0.1 |
| Volatility | 0.90 ✓ | 0.5 | 0.3 |
| **综合** | **0.90** | **0.4** | **0.2** |

## 7. 扩展指南

### 7.1 添加 Isolation Forest

```python
from sklearn.ensemble import IsolationForest
import numpy as np

class IsolationForestDetector(BaseDetector):
    """隔离森林异常检测"""

    def detect(
        self,
        prices: list[float],
        dates: list[date],
    ) -> DetectionResult:
        # 构造特征
        X = np.array(prices).reshape(-1, 1)

        # 训练模型
        model = IsolationForest(
            contamination=0.05,  # 预期异常比例
            random_state=42,
        )
        model.fit(X[:-1])  # 不包含当前点

        # 预测
        scores = model.score_samples(X)

        # 转换为 0-1 分数
        normalized_scores = (scores - scores.min()) / (scores.max() - scores.min())

        return self._build_result(prices, dates, 1 - normalized_scores)
```

### 7.2 添加 LSTM 检测

```python
class LstmAnomalyDetector(BaseDetector):
    """基于 LSTM 的异常检测"""

    def detect(self, prices, dates):
        # 重构误差检测
        # 正常模式重构误差小
        # 异常模式重构误差大
        ...
```

## 8. 性能优化

### 8.1 向量化计算

```python
# 避免 Python 循环
import numpy as np

def detect_fast(prices: list[float]) -> list[float]:
    prices_arr = np.array(prices)
    mean = prices_arr[:-1].mean()
    std = prices_arr[:-1].std()
    z_scores = np.abs((prices_arr - mean) / std)
    scores = 1 / (1 + np.exp(-(z_scores - 2)))
    return scores
```

### 8.2 缓存基准值

```python
class CachedZScoreDetector(BaseDetector):
    """带缓存的 Z-Score 检测器"""

    def __init__(self, config: DetectionConfig):
        super().__init__(config)
        self._cache: dict[str, tuple[float, float]] = {}

    def detect(self, prices, dates):
        cache_key = f"{len(prices)}"
        if cache_key not in self._cache:
            self._cache[cache_key] = (mean, std)
        return self._detect_impl(prices, dates)
```

## 9. 测试策略

```python
def test_zscore_normal():
    """正常数据不应被标记为异常"""
    prices = [100.0] * 50  # 恒定价格
    dates = [date(2024, 1, i) for i in range(1, 51)]

    config = DetectionConfig(threshold=0.8, lookback_period=30)
    detector = ZScoreDetector(config)

    result = detector.detect(prices, dates)
    assert result.anomaly_count == 0

def test_zscore_spike():
    """价格突增应被检测为异常"""
    prices = [100.0] * 50 + [150.0]  # 最后一天暴涨
    dates = [date(2024, 1, i) for i in range(1, 52)]

    config = DetectionConfig(threshold=0.8, lookback_period=30)
    detector = ZScoreDetector(config)

    result = detector.detect(prices, dates)
    assert result.anomaly_count > 0
    assert dates[-1] in result.anomaly_dates
```

## 10. 与其他模块集成

### 10.1 与 data 模块集成

```python
# data 采集 → ml 检测
async def collect_and_detect(symbol: str):
    collector = StockCollector()
    data = await collector.collect(symbol, start, end)

    # 提取价格序列
    prices = [d.close for d in data]
    dates = [d.date for d in data]

    # 检测异常
    detector = ZScoreDetector(config)
    result = detector.detect(prices, dates)

    return result
```

### 10.2 与 app 模块集成

```python
# API 查询异常
@router.get("/anomalies/{symbol}")
def get_anomalies(symbol: str):
    # 从数据库读取
    anomalies = anomaly_service.list_by_symbol(symbol)

    # 调用检测器重新检测
    prices = [a.value for a in anomalies]
    dates = [a.date for a in anomalies]

    detector = ZScoreDetector(config)
    result = detector.detect(prices, dates)

    return result
```

### 10.3 与 graph 模块集成

```python
# LangGraph 节点
def anomaly_detect_node(state: AnalysisState):
    symbol = state["symbol"]
    dates = state["dates"]

    # 采集数据
    prices = collect_prices(symbol, dates)

    # 检测异常
    config = DetectionConfig(detector_type=DetectorType.ZSCORE)
    result = ZScoreDetector(config).detect(prices, dates)

    return {
        "anomalies": result.anomaly_dates,
        "anomaly_scores": result.scores,
    }
```
