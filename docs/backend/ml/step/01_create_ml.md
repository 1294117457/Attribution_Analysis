# ML 模块开发步骤

## 概述

`ml` 模块负责机器学习相关功能：
- **detector**: 异常检测（Z-Score、IQR、波动率）
- **predictor**: 价格预测（LSTM、XGBoost）
- **classifier**: 分类器（情感分类）
- **features**: 特征工程

---

## 开发步骤

### Step 1: 创建目录结构

```
backend/ml/
├── __init__.py
├── config.py                  # ML 配置
│
├── models/                    # ML 模型定义
│   ├── __init__.py
│   ├── anomaly.py            # 异常检测模型
│   ├── prediction.py         # 预测模型
│   ├── classifier.py         # 分类模型
│   └── feature.py           # 特征模型
│
├── detector/                  # 异常检测器
│   ├── __init__.py
│   ├── base.py              # BaseDetector
│   ├── zscore_detector.py
│   ├── iqr_detector.py
│   └── volatility_detector.py
│
├── predictor/                 # 预测器
│   ├── __init__.py
│   ├── base.py              # BasePredictor
│   ├── lstm_predictor.py    # LSTM 预测
│   └── xgb_predictor.py    # XGBoost 预测
│
├── classifier/                # 分类器
│   ├── __init__.py
│   ├── base.py              # BaseClassifier
│   └── sentiment_classifier.py  # 情感分类
│
├── features/                  # 特征工程
│   ├── __init__.py
│   ├── technical.py         # 技术指标
│   ├── statistical.py       # 统计特征
│   └── sentiment.py         # 情感特征
│
└── scripts/                  # ML 脚本
    ├── __init__.py
    ├── train_predictor.py   # 训练预测器
    └── evaluate_detector.py  # 评估检测器
```

### Step 2: ML 配置 (`config.py`)

```python
from pydantic_settings import BaseSettings
from core.config import get_settings

class MLConfig(BaseSettings):
    """ML 模块配置"""

    # 模型路径
    MODEL_PATH: str = "./data/models"

    # 检测器默认配置
    DETECTOR_THRESHOLD: float = 0.80
    DETECTOR_LOOKBACK: int = 30

    # 预测器默认配置
    PREDICTOR_WINDOW: int = 20
    PREDICTOR_HORIZON: int = 5

    # 分类器默认配置
    CLASSIFIER_MODEL: str = "vader"  # vader / openai / local

    class Config:
        env_prefix = "ML_"
```

### Step 3: 预测模型 (`models/prediction.py`)

```python
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional
from enum import Enum

class PredictorType(str, Enum):
    """预测器类型"""
    LSTM = "lstm"
    XGBOOST = "xgboost"
    ENSEMBLE = "ensemble"

class PredictionResult(BaseModel):
    """预测结果"""
    symbol: str
    predictor_type: PredictorType
    date: date
    predicted_price: float
    confidence: float = Field(..., ge=0, le=1)
    predicted_direction: str = Field(..., pattern="^(up|down|neutral)$")
    actual_price: Optional[float] = None

class PredictionRequest(BaseModel):
    """预测请求"""
    symbol: str
    start_date: date
    end_date: date
    horizon: int = Field(5, description="预测未来 N 天", ge=1, le=30)
```

### 4: 分类模型 (`models/classifier.py`)

```python
from pydantic import BaseModel
from datetime import date
from enum import Enum
from typing import Optional

class SentimentLabel(str, Enum):
    """情感标签"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

class ClassificationResult(BaseModel):
    """分类结果"""
    text: str
    label: SentimentLabel
    score: float  # 0-1 置信度
    details: Optional[dict] = None

class SentimentAnalysisResult(BaseModel):
    """情感分析结果"""
    symbol: str
    date: date
    title: str
    sentiment: SentimentLabel
    confidence: float
    keywords: list[str]
    summary: str
```

### Step 5: 技术指标 (`features/technical.py`)

```python
import math
from typing import Optional

class TechnicalIndicators:
    """技术指标计算"""

    @staticmethod
    def sma(prices: list[float], period: int) -> list[float]:
        """简单移动平均 SMA"""
        if len(prices) < period:
            return []
        result = []
        for i in range(period - 1, len(prices)):
            avg = sum(prices[i - period + 1:i + 1]) / period
            result.append(round(avg, 2))
        return result

    @staticmethod
    def ema(prices: list[float], period: int) -> list[float]:
        """指数移动平均 EMA"""
        if len(prices) < period:
            return []
        multiplier = 2 / (period + 1)
        result = [sum(prices[:period]) / period]
        for price in prices[period:]:
            ema = (price - result[-1]) * multiplier + result[-1]
            result.append(round(ema, 2))
        return result

    @staticmethod
    def rsi(prices: list[float], period: int = 14) -> list[float]:
        """相对强弱指数 RSI"""
        if len(prices) < period + 1:
            return []

        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [c if c > 0 else 0 for c in changes]
        losses = [-c if c < 0 else 0 for c in changes]

        result = []
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        for i in range(period, len(changes)):
            if i > period:
                avg_gain = (avg_gain * (period - 1) + gains[i]) / period
                avg_loss = (avg_loss * (period - 1) + losses[i]) / period

            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            result.append(round(rsi, 2))

        return result

    @staticmethod
    def macd(
        prices: list[float],
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> dict[str, list[float]]:
        """MACD 指标"""
        ema_fast = TechnicalIndicators.ema(prices, fast)
        ema_slow = TechnicalIndicators.ema(prices, slow)

        if len(ema_fast) < len(ema_slow):
            return {"macd": [], "signal": [], "hist": []}

        macd_line = [f - s for f, s in zip(ema_fast[-len(ema_slow):], ema_slow)]
        signal_line = TechnicalIndicators.ema(macd_line, signal)
        hist = [m - s for m, s in zip(macd_line[-len(signal_line):], signal_line)]

        return {
            "macd": [round(m, 2) for m in macd_line],
            "signal": [round(s, 2) for s in signal_line],
            "hist": [round(h, 2) for h in hist],
        }

    @staticmethod
    def bollinger_bands(
        prices: list[float],
        period: int = 20,
        std_dev: int = 2,
    ) -> dict[str, list[float]]:
        """布林带"""
        sma_values = TechnicalIndicators.sma(prices, period)
        if len(sma_values) == 0:
            return {"upper": [], "middle": [], "lower": []}

        upper = []
        middle = sma_values
        lower = []

        for i in range(len(sma_values)):
            idx = i + period - 1
            window = prices[idx - period + 1:idx + 1]
            mean = sum(window) / period
            variance = sum((x - mean) ** 2 for x in window) / period
            std = math.sqrt(variance)
            upper.append(round(mean + std_dev * std, 2))
            lower.append(round(mean - std_dev * std, 2))

        return {
            "upper": upper,
            "middle": middle,
            "lower": lower,
        }
```

### Step 6: 基础预测器 (`predictor/base.py`)

```python
from abc import ABC, abstractmethod
from datetime import date
from ml.models.prediction import PredictionResult, PredictorType

class BasePredictor(ABC):
    """预测器基类"""

    def __init__(self):
        self.predictor_type: PredictorType

    @abstractmethod
    def predict(
        self,
        prices: list[float],
        dates: list[date],
        horizon: int = 5,
    ) -> list[PredictionResult]:
        """预测未来价格"""
        pass

    @abstractmethod
    def train(self, prices: list[float], dates: list[date]) -> None:
        """训练模型"""
        pass
```

### Step 7: LSTM 预测器 (`predictor/lstm_predictor.py`)

```python
import numpy as np
from datetime import date, timedelta
from ml.predictor.base import BasePredictor
from ml.models.prediction import PredictionResult, PredictorType

class LSTMPredictor(BasePredictor):
    """LSTM 价格预测器"""

    def __init__(self, window: int = 20):
        super().__init__()
        self.predictor_type = PredictorType.LSTM
        self.window = window
        self.model = None  # 后续实现

    def train(self, prices: list[float], dates: list[date]) -> None:
        """训练 LSTM 模型"""
        # TODO: 使用 PyTorch/TensorFlow 实现
        pass

    def predict(
        self,
        prices: list[float],
        dates: list[date],
        horizon: int = 5,
    ) -> list[PredictionResult]:
        """预测未来价格"""
        if len(prices) < self.window:
            raise ValueError(f"需要至少 {self.window} 个数据点")

        # TODO: 实际 LSTM 预测
        # 目前返回简单的线性外推作为占位

        last_price = prices[-1]
        results = []

        for i in range(1, horizon + 1):
            results.append(PredictionResult(
                symbol="",
                predictor_type=self.predictor_type,
                date=dates[-1] + timedelta(days=i),
                predicted_price=last_price,  # 占位
                confidence=0.5,
                predicted_direction="neutral",
            ))

        return results
```

### Step 8: 情感分类器 (`classifier/sentiment_classifier.py`)

```python
from typing import Optional
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from ml.classifier.base import BaseClassifier
from ml.models.classifier import (
    ClassificationResult,
    SentimentAnalysisResult,
    SentimentLabel,
)

class VADERClassifier(BaseClassifier):
    """VADER 情感分类器"""

    def __init__(self):
        super().__init__()
        self.analyzer = SentimentIntensityAnalyzer()

    def classify(self, text: str) -> ClassificationResult:
        """情感分类"""
        scores = self.analyzer.polarity_scores(text)
        compound = scores["compound"]

        if compound >= 0.05:
            label = SentimentLabel.POSITIVE
        elif compound <= -0.05:
            label = SentimentLabel.NEGATIVE
        else:
            label = SentimentLabel.NEUTRAL

        return ClassificationResult(
            text=text,
            label=label,
            score=abs(compound),  # 置信度
            details={
                "pos": scores["pos"],
                "neg": scores["neg"],
                "neu": scores["neu"],
                "compound": compound,
            },
        )

    def analyze_news(
        self,
        title: str,
        content: str,
        symbol: str,
        date: date,
    ) -> SentimentAnalysisResult:
        """分析新闻情感"""
        full_text = f"{title}. {content}"

        # 分类标题和内容
        title_result = self.classify(title)
        content_result = self.classify(content)

        # 综合判断
        if title_result.label == content_result.label:
            final_label = title_result.label
            final_score = (title_result.score + content_result.score) / 2
        else:
            # 标题权重更高
            final_label = title_result.label
            final_score = (title_result.score * 0.6 + content_result.score * 0.4)

        return SentimentAnalysisResult(
            symbol=symbol,
            date=date,
            title=title,
            sentiment=final_label,
            confidence=final_score,
            keywords=self._extract_keywords(full_text),
            summary=self._summarize(title_result, content_result),
        )

    def _extract_keywords(self, text: str) -> list[str]:
        """提取关键词（简化版）"""
        # TODO: 使用 NLP 库提取
        return []

    def _summarize(
        self,
        title_result: ClassificationResult,
        content_result: ClassificationResult,
    ) -> str:
        """生成摘要"""
        if title_result.label == SentimentLabel.POSITIVE:
            return "新闻情绪偏向正面"
        elif title_result.label == SentimentLabel.NEGATIVE:
            return "新闻情绪偏向负面"
        return "新闻情绪中性"
```

---

## 验证清单

### 异常检测
- [ ] ZScoreDetector 能检测价格异常
- [ ] IQRDetector 能检测价格异常
- [ ] VolatilityDetector 能检测波动率异常
- [ ] 技术指标计算正确（MA、RSI、MACD、布林带）

### 预测
- [ ] BasePredictor 接口定义正确
- [ ] LSTM 预测器能返回预测结果

### 分类
- [ ] VADER 情感分类器能正确分类
- [ ] 新闻情感分析能返回结果

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
│   ├── prediction.py
│   ├── classifier.py
│   └── feature.py
│
├── detector/
│   ├── __init__.py
│   ├── base.py
│   ├── zscore_detector.py
│   ├── iqr_detector.py
│   └── volatility_detector.py
│
├── predictor/
│   ├── __init__.py
│   ├── base.py
│   ├── lstm_predictor.py
│   └── xgb_predictor.py
│
├── classifier/
│   ├── __init__.py
│   ├── base.py
│   └── sentiment_classifier.py
│
├── features/
│   ├── __init__.py
│   ├── technical.py
│   └── statistical.py
│
└── scripts/
    ├── __init__.py
    ├── train_predictor.py
    └── evaluate_detector.py
```
