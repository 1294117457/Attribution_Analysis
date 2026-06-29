# ML 模块设计分析

## 1. 模块定位

```
┌─────────────────────────────────────────────────────────────────┐
│                      data/ (数据采集层)                          │
│   提供原始 K 线数据和新闻数据                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        ml/ (机器学习层)                          │
│                                                                 │
│   detector/ ───────▶ 异常检测                                    │
│   predictor/ ──────▶ 价格预测                                    │
│   classifier/ ─────▶ 情感分类                                    │
│   features/ ───────▶ 特征工程                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      graph/ (编排层)                            │
│   协调多个 ML 模块的工作                                          │
└─────────────────────────────────────────────────────────────────┘
```

## 2. 子模块职责

| 子模块 | 职责 | 输入 | 输出 |
|--------|------|------|------|
| `detector/` | 异常检测 | 价格/成交量序列 | 异常日期列表 |
| `predictor/` | 价格预测 | 历史价格 | 未来价格预测 |
| `classifier/` | 情感分类 | 新闻文本 | 情感标签 |
| `features/` | 特征工程 | 原始数据 | 技术指标 |

## 3. 检测器设计

### 3.1 检测器类型对比

```
┌──────────────────────────────────────────────────────────────────┐
│                        异常检测器                                  │
├─────────────┬─────────────┬─────────────┬──────────────────────┤
│  Z-Score    │     IQR     │  Volatility │   Isolation Forest   │
├─────────────┼─────────────┼─────────────┼──────────────────────┤
│ 偏离均值    │ 四分位距    │  波动率变化  │ 机器学习             │
│ N个标准差   │ 边界检测    │             │                     │
├─────────────┼─────────────┼─────────────┼──────────────────────┤
│ 正常分布    │ 非正态分布  │  极端行情    │ 复杂模式             │
│ 数据        │ 数据        │             │                     │
└─────────────┴─────────────┴─────────────┴──────────────────────┘
```

### 3.2 分数归一化

所有检测器输出 0-1 分数：

```
分数分布:
0.0 ──────────────────────────────────────── 1.0
│          │          │          │          │
正常      可疑       异常       高度异常
```

## 4. 技术指标设计

### 4.1 指标分类

```
┌─────────────────────────────────────────────────────────────────┐
│                       技术指标                                    │
├─────────────────────────────────────────────────────────────────┤
│  趋势类           │  动量类           │  波动类                 │
│  ───────────────  │  ───────────────  │  ───────────────        │
│  MA (均线)        │  RSI (相对强弱)    │  Bollinger (布林带)     │
│  EMA (指数均线)   │  MACD (平滑异同)   │  ATR (平均真实波幅)     │
│  KAMA (自适应)    │  Stochastic       │  Standard Deviation    │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 指标计算示例

```python
# SMA (简单移动平均)
SMA(5) = (P1 + P2 + P3 + P4 + P5) / 5

# EMA (指数移动平均)
EMA(5) = Close * 2/(5+1) + EMA_prev * (1 - 2/(5+1))

# RSI
RSI = 100 - (100 / (1 + RS))
RS = 平均涨幅 / 平均跌幅
```

## 5. 预测器设计

### 5.1 预测流程

```
历史数据 ──▶ 特征工程 ──▶ 模型预测 ──▶ 后处理 ──▶ 预测结果
  │            │                        │            │
  │            │                        │            │
[价格序列]   [技术指标]              [过滤/平滑]  [未来N天]
```

### 5.2 预测器类型

| 类型 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| LSTM | 能捕捉时序依赖 | 需要大量数据 | 短期预测 |
| XGBoost | 鲁棒、可解释 | 不擅长时序 | 分类/回归 |
| 集成 | 综合多模型优点 | 计算量大 | 综合分析 |

## 6. 情感分类设计

### 6.1 分类流程

```
新闻文本 ──▶ 预处理 ──▶ 情感分析 ──▶ 后处理 ──▶ 分类结果
   │          │            │            │
   │     [分词/去噪]  [VADER/LLM]   [阈值判断]
```

### 6.2 分类器类型

| 类型 | 优点 | 缺点 | 延迟 |
|------|------|------|------|
| VADER | 快速、无需 API | 精度一般 | <10ms |
| OpenAI | 高精度 | 成本、延迟 | >1s |
| 本地 LLM | 私密、可定制 | 资源消耗 | >5s |

## 7. 特征工程设计

### 7.1 特征类型

```python
# 价格特征
PriceFeature:
    - close, open, high, low
    - change_pct, returns

# 技术特征
TechnicalFeature:
    - ma5, ma10, ma20
    - rsi, macd, macd_signal, macd_hist
    - boll_upper, boll_middle, boll_lower

# 统计特征
StatisticalFeature:
    - mean, std, z_score
    - skewness, kurtosis

# 市场特征
MarketFeature:
    - market_return
    - industry_return
    - volume_ratio
```

### 7.2 特征选择

```python
# 时序特征窗口
WINDOW_SIZE = 20  # 20天历史数据

# 输出特征
FEATURE_DIM = 30  # 30维特征向量
```

## 8. 配置管理

```python
# ml/config.py
class MLConfig:
    # 检测器
    DETECTOR_THRESHOLD: float = 0.80
    DETECTOR_LOOKBACK: int = 30

    # 预测器
    PREDICTOR_WINDOW: int = 20
    PREDICTOR_HORIZON: int = 5

    # 分类器
    CLASSIFIER_MODEL: str = "vader"
```

## 9. 扩展指南

### 9.1 添加新检测器

```python
class IsolationForestDetector(BaseDetector):
    def detect(self, prices, dates):
        from sklearn.ensemble import IsolationForest
        model = IsolationForest()
        # 实现...
```

### 9.2 添加新预测器

```python
class TransformerPredictor(BasePredictor):
    def predict(self, prices, dates, horizon):
        # 使用 Transformer 模型
        ...
```

## 10. 性能优化

### 10.1 向量化计算

```python
import numpy as np

# 避免 Python 循环
def calc_ma_fast(prices: list[float], period: int) -> list[float]:
    arr = np.array(prices)
    return np.convolve(arr, np.ones(period)/period, mode='valid')
```

### 10.2 模型缓存

```python
class CachedPredictor(BasePredictor):
    def __init__(self):
        self._model_cache = {}

    def predict(self, symbol: str, ...):
        if symbol not in self._model_cache:
            self._model_cache[symbol] = self._load_model(symbol)
        return self._predict_impl(self._model_cache[symbol], ...)
```

## 11. 测试策略

```python
def test_technical_indicators():
    prices = [100 + i * 0.5 for i in range(50)]

    # 测试 MA
    ma5 = TechnicalIndicators.sma(prices, 5)
    assert len(ma5) == 46

    # 测试 RSI
    rsi = TechnicalIndicators.rsi(prices)
    assert all(0 <= r <= 100 for r in rsi)

def test_sentiment_classifier():
    classifier = VADERClassifier()

    result = classifier.classify("股票大涨，投资者信心十足")
    assert result.label == SentimentLabel.POSITIVE

    result = classifier.classify("公司业绩大幅下滑")
    assert result.label == SentimentLabel.NEGATIVE
```

## 12. 与其他模块集成

### 12.1 集成流程图

```
data/collect ──▶ ml/features ──▶ ml/detector ──▶ 异常告警
    │                                    │
    │                                    ▼
    │                              ml/classifier (分析原因)
    │
    ▼
ml/predictor ──▶ 预测结果 ──▶ graph/ 编排
```

### 12.2 数据流

```
prices: list[float]  ──▶ detector.detect() ──▶ anomaly_scores
                                      │
prices: list[float]  ──▶ features.calc() ──▶ technical_indicators
                                      │
                                      ▼
                            predictor.predict() ──▶ predictions
```
