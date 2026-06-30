# Analysis 分析模块设计

## 概述

分析模块是智能金融归因分析平台的核心，负责技术指标计算、异常检测和归因分析。

**特点**：作为独立模块，可被 `app/`（HTTP API）和 `graph/`（Agent）同时调用。

---

## 目录结构（采用依赖倒置）

```
backend/
├── app/                     # FastAPI 应用层
│   └── api/v1/
│       └── analysis.py      # 分析 API（调用 analysis 模块）
│
├── analysis/                # 分析模块（独立）
│   ├── __init__.py
│   ├── schemas.py           # 数据模型
│   ├── indicators.py       # 技术指标计算
│   │
│   ├── interfaces/          # 接口定义（依赖倒置）
│   │   ├── __init__.py
│   │   └── detector.py     # DetectorProtocol
│   │
│   ├── detectors/           # 具体检测器实现
│   │   ├── __init__.py
│   │   ├── rsi_detector.py
│   │   ├── macd_detector.py
│   │   ├── kdj_detector.py
│   │   ├── boll_detector.py
│   │   └── zscore_detector.py
│   │
│   ├── services/           # 服务层（使用接口）
│   │   ├── __init__.py
│   │   ├── detector_service.py   # 检测器服务
│   │   └── analysis_service.py   # 分析服务
│   │
│   └── attribution/        # 归因分析（未来）
│       └── ...
│
├── data/                   # 数据采集层
│   ├── interfaces/
│   ├── adapters/
│   └── ...
│
└── graph/                  # Graph Agent（未来）
    └── ...
```

### 依赖倒置原则

```
                    ┌─────────────────┐
                    │   interfaces/   │  ← 定义协议
                    │ DetectorProtocol│
                    └────────┬────────┘
                             │ 上层依赖抽象
                             ▼
┌─────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  detectors/ │────▶│   services/     │◀────│   app/          │
│ (实现协议)  │     │ DetectorService │     │  API 层         │
└─────────────┘     └────────┬────────┘     └─────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    schemas/     │  ← 核心数据模型
                    └─────────────────┘
```

**好处**：
- `DetectorService` 不关心具体用什么检测器
- 可自由替换/组合检测器
- 易于扩展新检测器
- 易于单元测试（Mock 检测器）

---

## 1. 数据模型 (`analysis/schemas.py`)

### 1.1 K 线数据

```python
"""K 线数据（从 data 层传入）"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class KlineData:
    """单条 K 线数据"""
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float = 0.0
    change_pct: float = 0.0
```

### 1.2 指标数据

```python
"""技术指标数据"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class IndicatorData:
    """技术指标数据"""
    date: date

    # 均线
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None

    # EMA
    ema12: Optional[float] = None
    ema26: Optional[float] = None

    # MACD
    dif: Optional[float] = None
    dea: Optional[float] = None
    macd_hist: Optional[float] = None

    # RSI
    rsi6: Optional[float] = None
    rsi12: Optional[float] = None

    # KDJ
    k: Optional[float] = None
    d: Optional[float] = None
    j: Optional[float] = None

    # BOLL
    boll_upper: Optional[float] = None
    boll_mid: Optional[float] = None
    boll_lower: Optional[float] = None
```

### 1.3 异常结果

```python
"""异常检测结果"""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional


class AnomalyType(str, Enum):
    """异常类型"""
    MA_DEVIATION = "ma_deviation"           # 均线偏离
    MACD_CROSS = "macd_cross"               # MACD 交叉
    MACD_DIVERGENCE = "macd_divergence"     # MACD 背离
    RSI_OVERBOUGHT = "rsi_overbought"       # RSI 超买
    RSI_OVERSOLD = "rsi_oversold"           # RSI 超卖
    KDJ_OVERBOUGHT = "kdj_overbought"       # KDJ 超买
    KDJ_OVERSOLD = "kdj_oversold"           # KDJ 超卖
    KDJ_BLINDING = "kdj_blinding"           # KDJ 钝化
    BOLL_BREAK_UPPER = "boll_break_upper"   # 突破上轨
    BOLL_BREAK_LOWER = "boll_break_lower"   # 突破下轨
    BOLL_SQUEEZE = "boll_squeeze"           # 布林带收窄
    PRICE_SPIKE = "price_spike"             # 价格异常波动
    VOLUME_SPIKE = "volume_spike"           # 成交量异常


class Severity(str, Enum):
    """异常严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AnomalyResult:
    """异常检测结果"""
    date: date
    anomaly_type: AnomalyType
    severity: Severity
    value: float
    threshold: float
    score: float          # 0-1，异常置信度
    description: str       # 异常描述
    details: Optional[dict] = None  # 额外详情


@dataclass
class AnomalyReport:
    """异常检测报告"""
    symbol: str
    start_date: date
    end_date: date
    total_klines: int
    anomalies: list[AnomalyResult]
    summary: dict          # 统计摘要
```

---

## 2. 技术指标计算 (`analysis/indicators.py`)

### 2.1 依赖

```bash
pip install pandas pandas-ta numpy
```

### 2.2 计算器实现

```python
"""技术指标计算器"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Optional

from .schemas import KlineData, IndicatorData


class IndicatorCalculator:
    """技术指标计算器"""

    def calculate_all(
        self,
        klines: list[KlineData],
    ) -> list[IndicatorData]:
        """
        计算所有技术指标

        Args:
            klines: K 线数据列表（按日期升序）

        Returns:
            包含技术指标的列表
        """
        df = self._to_dataframe(klines)

        # 均线 MA
        df["ma5"] = ta.sma(df["close"], length=5)
        df["ma10"] = ta.sma(df["close"], length=10)
        df["ma20"] = ta.sma(df["close"], length=20)
        df["ma60"] = ta.sma(df["close"], length=60)

        # EMA
        df["ema12"] = ta.ema(df["close"], length=12)
        df["ema26"] = ta.ema(df["close"], length=26)

        # MACD
        macd = ta.macd(df["close"])
        df["dif"] = macd["MACD_12_26_9"]
        df["dea"] = macd["MACDs_12_26_9"]
        df["macd_hist"] = macd["MACDh_12_26_9"]

        # RSI
        df["rsi6"] = ta.rsi(df["close"], length=6)
        df["rsi12"] = ta.rsi(df["close"], length=12)

        # KDJ（pandas-ta 没有，自己实现）
        kdj = self._calc_kdj(df["high"], df["low"], df["close"])
        df["k"] = kdj["k"]
        df["d"] = kdj["d"]
        df["j"] = kdj["j"]

        # BOLL
        boll = ta.bbands(df["close"], length=20)
        df["boll_upper"] = boll["BBU_20_2.0"]
        df["boll_mid"] = boll["BBM_20_2.0"]
        df["boll_lower"] = boll["BBL_20_2.0"]

        return self._to_indicator_list(df)

    def _to_dataframe(self, klines: list[KlineData]) -> pd.DataFrame:
        """转换为 DataFrame"""
        return pd.DataFrame([{
            "date": k.date,
            "open": k.open,
            "high": k.high,
            "low": k.low,
            "close": k.close,
            "volume": k.volume,
        } for k in klines])

    def _to_indicator_list(self, df: pd.DataFrame) -> list[IndicatorData]:
        """转换为 IndicatorData 列表"""
        return [
            IndicatorData(
                date=row["date"],
                ma5=row.get("ma5"),
                ma10=row.get("ma10"),
                ma20=row.get("ma20"),
                ma60=row.get("ma60"),
                ema12=row.get("ema12"),
                ema26=row.get("ema26"),
                dif=row.get("dif"),
                dea=row.get("dea"),
                macd_hist=row.get("macd_hist"),
                rsi6=row.get("rsi6"),
                rsi12=row.get("rsi12"),
                k=row.get("k"),
                d=row.get("d"),
                j=row.get("j"),
                boll_upper=row.get("boll_upper"),
                boll_mid=row.get("boll_mid"),
                boll_lower=row.get("boll_lower"),
            )
            for _, row in df.iterrows()
        ]

    def _calc_kdj(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        n: int = 9,
    ) -> dict:
        """
        计算 KDJ 指标

        RSV = (C - L) / (H - L) * 100
        K = 2/3 * K(-1) + 1/3 * RSV
        D = 2/3 * D(-1) + 1/3 * K
        J = 3K - 2D
        """
        # 计算 RSV
        lowest_low = low.rolling(window=n).min()
        highest_high = high.rolling(window=n).max()
        rsv = (close - lowest_low) / (highest_high - lowest_low) * 100

        # 计算 K, D
        k = rsv.copy()
        d = rsv.copy()
        for i in range(1, len(k)):
            if pd.notna(k.iloc[i - 1]):
                k.iloc[i] = 2 / 3 * k.iloc[i - 1] + 1 / 3 * rsv.iloc[i]
                d.iloc[i] = 2 / 3 * d.iloc[i - 1] + 1 / 3 * k.iloc[i]

        # 计算 J
        j = 3 * k - 2 * d

        return {"k": k, "d": d, "j": j}
```

---

## 5. 接口定义 (`analysis/interfaces/detector.py`)

### 5.1 检测器协议

```python
"""检测器接口定义（依赖倒置）"""

from typing import Protocol
from typing_extensions import Self

from ..schemas import KlineData, IndicatorData, AnomalyResult


class DetectorProtocol(Protocol):
    """检测器协议：所有异常检测器必须满足此协议

    采用依赖倒置原则：
    - services/detector_service.py 只依赖此协议
    - detectors/ 下的具体实现不感知服务层
    """

    @property
    def name(self) -> str:
        """检测器名称"""
        ...

    @property
    def description(self) -> str:
        """检测器描述"""
        ...

    def detect(
        self,
        klines: list[KlineData],
        indicators: list[IndicatorData],
    ) -> list[AnomalyResult]:
        """
        检测异常

        Args:
            klines: K 线数据（按日期升序）
            indicators: 技术指标数据

        Returns:
            异常结果列表
        """
        ...


class DetectorFactory:
    """检测器工厂（可选，用于创建检测器）"""

    _registry: dict[str, type[DetectorProtocol]] = {}

    @classmethod
    def register(cls, name: str) -> callable:
        """注册检测器"""
        def decorator(detector_cls: type[DetectorProtocol]) -> type[DetectorProtocol]:
            cls._registry[name] = detector_cls
            return detector_cls
        return decorator

    @classmethod
    def create(cls, name: str) -> DetectorProtocol:
        """创建检测器"""
        if name not in cls._registry:
            raise ValueError(f"Unknown detector: {name}")
        return cls._registry[name]()

    @classmethod
    def list_detectors(cls) -> list[str]:
        """列出所有注册的检测器"""
        return list(cls._registry.keys())
```

---

## 4. 具体检测器实现 (`analysis/detectors/`)

### 4.1 RSI 检测器

```python
"""RSI 异常检测器"""

from typing import Optional

from ..schemas import (
    KlineData, IndicatorData, AnomalyResult,
    AnomalyType, Severity
)
from ..interfaces.detector import DetectorProtocol, DetectorFactory


@DetectorFactory.register("rsi")
class RSIDetector(DetectorProtocol):
    """RSI 异常检测器"""

    OVERBOUGHT = 70       # 超买阈值
    OVERSOLD = 30         # 超卖阈值
    CRITICAL_OVERBOUGHT = 80
    CRITICAL_OVERSOLD = 20

    @property
    def name(self) -> str:
        return "RSI Detector"

    @property
    def description(self) -> str:
        return "检测 RSI 超买超卖异常"

    def detect(
        self,
        klines: list[KlineData],
        indicators: list[IndicatorData],
    ) -> list[AnomalyResult]:
        anomalies = []

        for ind in indicators:
            if ind.rsi6 is None:
                continue

            anomaly = self._detect_single(ind)
            if anomaly:
                anomalies.append(anomaly)

        return anomalies

    def _detect_single(self, ind: IndicatorData) -> Optional[AnomalyResult]:
        """检测单个数据点"""
        rsi = ind.rsi6

        if rsi >= self.CRITICAL_OVERBOUGHT:
            return AnomalyResult(
                date=ind.date,
                anomaly_type=AnomalyType.RSI_OVERBOUGHT,
                severity=Severity.CRITICAL,
                value=rsi,
                threshold=self.OVERBOUGHT,
                score=self._calculate_score(rsi, self.OVERBOUGHT),
                description=f"RSI 严重超买: {rsi:.2f}",
            )
        elif rsi >= self.OVERBOUGHT:
            return AnomalyResult(
                date=ind.date,
                anomaly_type=AnomalyType.RSI_OVERBOUGHT,
                severity=Severity.MEDIUM,
                value=rsi,
                threshold=self.OVERBOUGHT,
                score=self._calculate_score(rsi, self.OVERBOUGHT),
                description=f"RSI 超买: {rsi:.2f}",
            )
        elif rsi <= self.CRITICAL_OVERSOLD:
            return AnomalyResult(
                date=ind.date,
                anomaly_type=AnomalyType.RSI_OVERSOLD,
                severity=Severity.CRITICAL,
                value=rsi,
                threshold=self.OVERSOLD,
                score=self._calculate_score(rsi, self.OVERSOLD),
                description=f"RSI 严重超卖: {rsi:.2f}",
            )
        elif rsi <= self.OVERSOLD:
            return AnomalyResult(
                date=ind.date,
                anomaly_type=AnomalyType.RSI_OVERSOLD,
                severity=Severity.MEDIUM,
                value=rsi,
                threshold=self.OVERSOLD,
                score=self._calculate_score(rsi, self.OVERSOLD),
                description=f"RSI 超卖: {rsi:.2f}",
            )

        return None

    def _calculate_score(self, value: float, threshold: float) -> float:
        """计算异常分数"""
        ratio = abs(value - threshold) / threshold
        return min(ratio, 1.0)
```

### 4.2 MACD 检测器

```python
"""MACD 异常检测器"""

from typing import Optional

from ..schemas import (
    KlineData, IndicatorData, AnomalyResult,
    AnomalyType, Severity
)
from ..interfaces.detector import DetectorProtocol, DetectorFactory


@DetectorFactory.register("macd")
class MACDDetector(DetectorProtocol):
    """MACD 异常检测器"""

    @property
    def name(self) -> str:
        return "MACD Detector"

    @property
    def description(self) -> str:
        return "检测 MACD 交叉和背离"

    def detect(
        self,
        klines: list[KlineData],
        indicators: list[IndicatorData],
    ) -> list[AnomalyResult]:
        anomalies = []

        for i, ind in enumerate(indicators):
            if i == 0 or ind.dif is None or indicators[i - 1].dif is None:
                continue

            # 检测交叉
            cross = self._detect_cross(ind, indicators[i - 1])
            if cross:
                anomalies.append(cross)

            # 检测背离
            if i >= 20:
                divergence = self._detect_divergence(klines[:i + 1], indicators[:i + 1])
                if divergence:
                    anomalies.append(divergence)

        return anomalies

    def _detect_cross(
        self,
        curr: IndicatorData,
        prev: IndicatorData,
    ) -> Optional[AnomalyResult]:
        """检测 MACD 交叉"""
        if prev.dif <= 0 < curr.dif:
            return AnomalyResult(
                date=curr.date,
                anomaly_type=AnomalyType.MACD_CROSS,
                severity=Severity.MEDIUM,
                value=curr.dif,
                threshold=0,
                score=min(abs(curr.dif) * 2, 1.0),
                description=f"MACD 金叉，DIF={curr.dif:.4f}",
            )
        elif prev.dif >= 0 > curr.dif:
            return AnomalyResult(
                date=curr.date,
                anomaly_type=AnomalyType.MACD_CROSS,
                severity=Severity.MEDIUM,
                value=curr.dif,
                threshold=0,
                score=min(abs(curr.dif) * 2, 1.0),
                description=f"MACD 死叉，DIF={curr.dif:.4f}",
            )
        return None

    def _detect_divergence(
        self,
        klines: list[KlineData],
        indicators: list[IndicatorData],
    ) -> Optional[AnomalyResult]:
        """检测 MACD 背离"""
        if len(klines) < 20:
            return None

        recent_klines = klines[-20:]
        recent_indicators = indicators[-20:]

        price_trend = recent_klines[-1].close - recent_klines[0].close
        dif_trend = recent_indicators[-1].dif - recent_indicators[0].dif

        prices = [k.close for k in recent_klines]
        if prices[-1] == max(prices) and price_trend > 0 and dif_trend < 0:
            return AnomalyResult(
                date=recent_indicators[-1].date,
                anomaly_type=AnomalyType.MACD_DIVERGENCE,
                severity=Severity.HIGH,
                value=dif_trend,
                threshold=0,
                score=0.8,
                description="MACD 顶背离：价格创新高但动能减弱",
            )

        if prices[-1] == min(prices) and price_trend < 0 and dif_trend > 0:
            return AnomalyResult(
                date=recent_indicators[-1].date,
                anomaly_type=AnomalyType.MACD_DIVERGENCE,
                severity=Severity.HIGH,
                value=dif_trend,
                threshold=0,
                score=0.8,
                description="MACD 底背离：价格创新低但动能增强",
            )

        return None
```

### 4.3 BOLL 检测器

```python
"""BOLL 异常检测器"""

from typing import Optional

from ..schemas import (
    KlineData, IndicatorData, AnomalyResult,
    AnomalyType, Severity
)
from ..interfaces.detector import DetectorProtocol, DetectorFactory


@DetectorFactory.register("boll")
class BOLLDetector(DetectorProtocol):
    """BOLL 异常检测器"""

    BREAK_THRESHOLD = 1.02
    SQUEEZE_PERCENTILE = 10

    @property
    def name(self) -> str:
        return "BOLL Detector"

    @property
    def description(self) -> str:
        return "检测 BOLL 突破和收窄"

    def detect(
        self,
        klines: list[KlineData],
        indicators: list[IndicatorData],
    ) -> list[AnomalyResult]:
        anomalies = []

        # 检测突破
        for i, ind in enumerate(indicators):
            if ind.boll_upper is None or ind.boll_lower is None:
                continue

            if i < len(klines):
                anomaly = self._detect_breakthrough(klines[i], ind)
                if anomaly:
                    anomalies.append(anomaly)

        # 检测收窄
        squeeze = self._detect_squeeze(indicators)
        if squeeze:
            anomalies.append(squeeze)

        return anomalies

    def _detect_breakthrough(
        self,
        kline: KlineData,
        ind: IndicatorData,
    ) -> Optional[AnomalyResult]:
        """检测突破"""
        if kline.close > ind.boll_upper * self.BREAK_THRESHOLD:
            return AnomalyResult(
                date=ind.date,
                anomaly_type=AnomalyType.BOLL_BREAK_UPPER,
                severity=Severity.HIGH,
                value=kline.close,
                threshold=ind.boll_upper,
                score=min((kline.close - ind.boll_upper) / ind.boll_upper, 1.0),
                description=f"突破布林上轨: {kline.close:.2f} > {ind.boll_upper:.2f}",
            )

        if kline.close < ind.boll_lower / self.BREAK_THRESHOLD:
            return AnomalyResult(
                date=ind.date,
                anomaly_type=AnomalyType.BOLL_BREAK_LOWER,
                severity=Severity.HIGH,
                value=kline.close,
                threshold=ind.boll_lower,
                score=min((ind.boll_lower - kline.close) / ind.boll_lower, 1.0),
                description=f"突破布林下轨: {kline.close:.2f} < {ind.boll_lower:.2f}",
            )

        return None

    def _detect_squeeze(
        self,
        indicators: list[IndicatorData],
    ) -> Optional[AnomalyResult]:
        """检测布林带收窄"""
        if len(indicators) < 20:
            return None

        bandwidths = []
        for ind in indicators[-60:]:
            if ind.boll_mid and ind.boll_upper and ind.boll_lower:
                bw = (ind.boll_upper - ind.boll_lower) / ind.boll_mid
                bandwidths.append(bw)

        if len(bandwidths) < 20:
            return None

        current = bandwidths[-1]
        percentile = (sum(1 for b in bandwidths if b < current) / len(bandwidths)) * 100

        if percentile <= self.SQUEEZE_PERCENTILE:
            return AnomalyResult(
                date=indicators[-1].date,
                anomaly_type=AnomalyType.BOLL_SQUEEZE,
                severity=Severity.HIGH,
                value=current,
                threshold=bandwidths[int(len(bandwidths) * 0.1)],
                score=percentile / 100,
                description=f"布林带极度收窄（历史{percentile:.0f}%分位），酝酿突破",
            )

        return None
```

### 4.5 Z-Score 检测器

```python
"""Z-Score 异常检测器"""

from typing import Optional
import statistics

from ..schemas import (
    KlineData, IndicatorData, AnomalyResult,
    AnomalyType, Severity
)
from ..interfaces.detector import DetectorProtocol, DetectorFactory


@DetectorFactory.register("zscore")
class ZScoreDetector(DetectorProtocol):
    """基于 Z-Score 的价格/成交量异常检测

    检测价格或成交量偏离均值超过 2 个标准差的情况
    """

    Z_THRESHOLD = 2.0  # 异常阈值

    @property
    def name(self) -> str:
        return "Z-Score Detector"

    @property
    def description(self) -> str:
        return "检测价格/成交量 Z-Score 异常"

    def detect(
        self,
        klines: list[KlineData],
        indicators: list[IndicatorData],
    ) -> list[AnomalyResult]:
        anomalies = []

        if len(klines) < 20:
            return anomalies

        # 计算价格 Z-Score
        prices = [k.close for k in klines]
        anomalies.extend(self._detect_zscore_anomalies(
            prices, klines, "price", AnomalyType.PRICE_SPIKE
        ))

        # 计算成交量 Z-Score
        volumes = [k.volume for k in klines]
        anomalies.extend(self._detect_zscore_anomalies(
            volumes, klines, "volume", AnomalyType.VOLUME_SPIKE
        ))

        return anomalies

    def _detect_zscore_anomalies(
        self,
        values: list[float],
        klines: list[KlineData],
        field_name: str,
        anomaly_type: AnomalyType,
    ) -> list[AnomalyResult]:
        """检测 Z-Score 异常"""
        anomalies = []

        if len(values) < 20:
            return anomalies

        mean = statistics.mean(values[-60:])  # 用最近 60 天
        stdev = statistics.stdev(values[-60:])

        if stdev == 0:
            return anomalies

        for i, value in enumerate(values[-20:]):  # 最近 20 天
            zscore = (value - mean) / stdev

            if abs(zscore) > self.Z_THRESHOLD:
                severity = Severity.CRITICAL if abs(zscore) > 3 else Severity.HIGH
                anomalies.append(AnomalyResult(
                    date=klines[i].date,
                    anomaly_type=anomaly_type,
                    severity=severity,
                    value=value,
                    threshold=mean,
                    score=min(abs(zscore) / 4, 1.0),
                    description=f"{field_name.capitalize()} Z-Score 异常: {zscore:.2f}σ",
                ))

        return anomalies
```

### 4.6 KDJ 检测器

```python
"""KDJ 异常检测器"""

from typing import Optional

from ..schemas import (
    KlineData, IndicatorData, AnomalyResult,
    AnomalyType, Severity
)
from ..interfaces.detector import DetectorProtocol, DetectorFactory


@DetectorFactory.register("kdj")
class KDJDetector(DetectorProtocol):
    """KDJ 异常检测器"""

    OVERBOUGHT = 80       # 超买阈值
    OVERSOLD = 20         # 超卖阈值
    CRITICAL_OVERBOUGHT = 90
    CRITICAL_OVERSOLD = 10

    @property
    def name(self) -> str:
        return "KDJ Detector"

    @property
    def description(self) -> str:
        return "检测 KDJ 超买超卖异常"

    def detect(
        self,
        klines: list[KlineData],
        indicators: list[IndicatorData],
    ) -> list[AnomalyResult]:
        anomalies = []

        for ind in indicators:
            if ind.k is None or ind.d is None or ind.j is None:
                continue

            anomaly = self._detect_single(ind)
            if anomaly:
                anomalies.append(anomaly)

            # 检测 KDJ 钝化
            blinding = self._detect_blinding(ind)
            if blinding:
                anomalies.append(blinding)

        return anomalies

    def _detect_single(self, ind: IndicatorData) -> Optional[AnomalyResult]:
        """检测单个数据点"""
        j = ind.j

        if j >= self.CRITICAL_OVERBOUGHT:
            return AnomalyResult(
                date=ind.date,
                anomaly_type=AnomalyType.KDJ_OVERBOUGHT,
                severity=Severity.CRITICAL,
                value=j,
                threshold=self.OVERBOUGHT,
                score=self._calculate_score(j, self.OVERBOUGHT),
                description=f"KDJ 严重超买: J={j:.2f}",
            )
        elif j >= self.OVERBOUGHT:
            return AnomalyResult(
                date=ind.date,
                anomaly_type=AnomalyType.KDJ_OVERBOUGHT,
                severity=Severity.MEDIUM,
                value=j,
                threshold=self.OVERBOUGHT,
                score=self._calculate_score(j, self.OVERBOUGHT),
                description=f"KDJ 超买: J={j:.2f}",
            )
        elif j <= self.CRITICAL_OVERSOLD:
            return AnomalyResult(
                date=ind.date,
                anomaly_type=AnomalyType.KDJ_OVERSOLD,
                severity=Severity.CRITICAL,
                value=j,
                threshold=self.OVERSOLD,
                score=self._calculate_score(j, self.OVERSOLD),
                description=f"KDJ 严重超卖: J={j:.2f}",
            )
        elif j <= self.OVERSOLD:
            return AnomalyResult(
                date=ind.date,
                anomaly_type=AnomalyType.KDJ_OVERSOLD,
                severity=Severity.MEDIUM,
                value=j,
                threshold=self.OVERSOLD,
                score=self._calculate_score(j, self.OVERSOLD),
                description=f"KDJ 超卖: J={j:.2f}",
            )

        return None

    def _detect_blinding(self, ind: IndicatorData) -> Optional[AnomalyResult]:
        """检测 KDJ 钝化（J 值持续高位或低位）"""
        # 简化实现：J > 100 或 J < -100 视为钝化
        if ind.j > 100:
            return AnomalyResult(
                date=ind.date,
                anomaly_type=AnomalyType.KDJ_BLINDING,
                severity=Severity.HIGH,
                value=ind.j,
                threshold=100,
                score=min((ind.j - 100) / 50, 1.0),
                description=f"KDJ 高位钝化: J={ind.j:.2f}",
            )
        elif ind.j < -100:
            return AnomalyResult(
                date=ind.date,
                anomaly_type=AnomalyType.KDJ_BLINDING,
                severity=Severity.HIGH,
                value=ind.j,
                threshold=-100,
                score=min((abs(ind.j) - 100) / 50, 1.0),
                description=f"KDJ 低位钝化: J={ind.j:.2f}",
            )
        return None

    def _calculate_score(self, value: float, threshold: float) -> float:
        """计算异常分数"""
        ratio = abs(value - threshold) / threshold
        return min(ratio, 1.0)
```

---

## 5. 检测器服务 (`analysis/services/detector_service.py`)

```python
"""检测器服务（使用 DetectorProtocol 接口）"""

from typing import Optional

from ..schemas import KlineData, IndicatorData, AnomalyResult, AnomalyReport, Severity
from ..interfaces.detector import DetectorProtocol, DetectorFactory


class DetectorService:
    """
    检测器服务

    - 不依赖具体检测器实现，只依赖 DetectorProtocol
    - 通过依赖注入或工厂创建具体检测器
    - 可组合多个检测器
    """

    def __init__(self, detectors: Optional[list[DetectorProtocol]] = None):
        """
        Args:
            detectors: 检测器列表，默认使用所有注册检测器
        """
        if detectors:
            self.detectors = detectors
        else:
            # 默认创建所有注册的检测器
            self.detectors = [
                DetectorFactory.create(name)
                for name in DetectorFactory.list_detectors()
            ]

    def detect(
        self,
        klines: list[KlineData],
        indicators: list[IndicatorData],
        detector_names: Optional[list[str]] = None,
    ) -> list[AnomalyResult]:
        """
        执行异常检测

        Args:
            klines: K 线数据
            indicators: 技术指标
            detector_names: 指定检测器名称（None 表示全部）

        Returns:
            所有异常结果
        """
        if detector_names:
            detectors = [
                DetectorFactory.create(name)
                for name in detector_names
                if name in DetectorFactory.list_detectors()
            ]
        else:
            detectors = self.detectors

        all_anomalies = []
        for detector in detectors:
            anomalies = detector.detect(klines, indicators)
            all_anomalies.extend(anomalies)

        # 按日期排序
        all_anomalies.sort(key=lambda x: x.date)

        return all_anomalies

    def detect_consensus(
        self,
        klines: list[KlineData],
        indicators: list[IndicatorData],
        min_count: int = 2,
    ) -> list[AnomalyResult]:
        """
        检测多指标共振异常

        Args:
            min_count: 最少异常指标数量
        """
        all_anomalies = self.detect(klines, indicators)

        # 按日期分组
        from collections import defaultdict
        by_date = defaultdict(list)
        for anomaly in all_anomalies:
            by_date[anomaly.date].append(anomaly)

        # 筛选共振异常
        consensus = []
        for date, anomalies in by_date.items():
            if len(anomalies) >= min_count:
                avg_score = sum(a.score for a in anomalies) / len(anomalies)
                types = [a.anomaly_type.value for a in anomalies]

                consensus.append(AnomalyResult(
                    date=date,
                    anomaly_type=anomalies[0].anomaly_type,
                    severity=Severity.HIGH if len(anomalies) >= 3 else Severity.MEDIUM,
                    value=avg_score,
                    threshold=min_count,
                    score=avg_score,
                    description=f"多指标共振（{len(anomalies)}个指标异常）: {', '.join(types)}",
                    details={"anomalies": anomalies},
                ))

        return consensus

    def generate_report(
        self,
        symbol: str,
        klines: list[KlineData],
        anomalies: list[AnomalyResult],
    ) -> AnomalyReport:
        """生成异常检测报告"""
        if not anomalies:
            return AnomalyReport(
                symbol=symbol,
                start_date=klines[0].date if klines else None,
                end_date=klines[-1].date if klines else None,
                total_klines=len(klines),
                anomalies=[],
                summary={"total": 0, "by_type": {}, "by_severity": {}},
            )

        by_type = {}
        by_severity = {}
        for a in anomalies:
            by_type[a.anomaly_type.value] = by_type.get(a.anomaly_type.value, 0) + 1
            by_severity[a.severity.value] = by_severity.get(a.severity.value, 0) + 1

        return AnomalyReport(
            symbol=symbol,
            start_date=klines[0].date,
            end_date=klines[-1].date,
            total_klines=len(klines),
            anomalies=anomalies,
            summary={
                "total": len(anomalies),
                "by_type": by_type,
                "by_severity": by_severity,
            },
        )
```

---

## 7. 分析服务 (`analysis/services/analysis_service.py`)

```python
"""分析服务（使用 DetectorService）"""

from ..schemas import KlineData, IndicatorData
from ..indicators import IndicatorCalculator
from .detector_service import DetectorService


class AnalysisService:
    """分析服务（组合所有功能）"""

    def __init__(self, detector_service: DetectorService = None):
        """
        Args:
            detector_service: 检测器服务，默认创建新的
        """
        self.calculator = IndicatorCalculator()
        self.detector_service = detector_service or DetectorService()

    def analyze(
        self,
        klines: list[KlineData],
        symbol: str = "",
        detect_anomalies: bool = True,
    ) -> dict:
        """
        完整分析流程

        Args:
            klines: K 线数据
            symbol: 股票代码
            detect_anomalies: 是否检测异常

        Returns:
            {
                "indicators": [...],
                "anomalies": [...],
                "report": {...}
            }
        """
        # 1. 计算技术指标
        indicators = self.calculator.calculate_all(klines)

        result = {
            "indicators": indicators,
            "anomalies": [],
            "report": None,
        }

        # 2. 检测异常
        if detect_anomalies:
            anomalies = self.detector_service.detect(klines, indicators)
            result["anomalies"] = anomalies

            # 3. 生成报告
            result["report"] = self.detector_service.generate_report(
                symbol=symbol,
                klines=klines,
                anomalies=anomalies,
            )

        return result
```

---

## 7. 模块入口 (`analysis/__init__.py`)

```python
"""分析模块主入口"""

from .schemas import (
    KlineData,
    IndicatorData,
    AnomalyResult,
    AnomalyType,
    Severity,
    AnomalyReport,
)
from .indicators import IndicatorCalculator
from .interfaces.detector import DetectorProtocol, DetectorFactory
from .detectors import RSIDetector, MACDDetector, BOLLDetector, ZScoreDetector, KDJDetector
from .services import DetectorService, AnalysisService


# 注册检测器
for detector_cls in [RSIDetector, MACDDetector, BOLLDetector, ZScoreDetector, KDJDetector]:
    name = detector_cls.__name__.replace("Detector", "").lower()
    DetectorFactory.register(name)(detector_cls)


__all__ = [
    # schemas
    "KlineData",
    "IndicatorData",
    "AnomalyResult",
    "AnomalyType",
    "Severity",
    "AnomalyReport",
    # interfaces
    "DetectorProtocol",
    "DetectorFactory",
    # detectors
    "RSIDetector",
    "MACDDetector",
    "BOLLDetector",
    "ZScoreDetector",
    "KDJDetector",
    # services
    "DetectorService",
    "AnalysisService",
]
```

---

## 8. API 层 (`app/api/v1/analysis.py`)

### 8.1 API Schema 定义 (`app/schemas.py`)

```python
"""API 响应模型"""

from pydantic import BaseModel, Field
from datetime import date
from typing import Optional


class AnomalyResponse(BaseModel):
    """异常响应"""
    date: str
    type: str
    severity: str
    score: float
    description: str


class IndicatorResponse(BaseModel):
    """指标响应"""
    date: str
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None
    rsi6: Optional[float] = None
    rsi12: Optional[float] = None
    macd_hist: Optional[float] = None
    k: Optional[float] = None
    d: Optional[float] = None
    j: Optional[float] = None


class AnalysisResponse(BaseModel):
    """分析响应"""
    symbol: str
    name: str = ""
    indicators_count: int = 0
    anomalies_count: int = 0
    summary: dict = Field(default_factory=dict)
```

### 8.2 API 路由实现

```python
"""分析 API"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import Optional

from app.dependencies import get_db
from app.schemas import AnalysisResponse, AnomalyResponse
from data.services import StockService
from analysis import AnalysisService, KlineData


router = APIRouter(prefix="/api/v1/analysis", tags=["分析"])


@router.get("/{symbol}/indicators", response_model=dict)
def get_indicators(
    symbol: str,
    days: int = Query(60, ge=10, le=500),
    db: Session = Depends(get_db),
):
    """
    获取股票技术指标

    - **symbol**: 股票代码
    - **days**: 查询天数（默认60天）
    """
    stock_service = StockService(db)
    klines_db = stock_service.get_klines(symbol, limit=days)

    if not klines_db:
        raise HTTPException(status_code=404, detail=f"未找到股票 {symbol} 的数据")

    # 转换为 KlineData（使用切片副本避免修改原数据）
    klines = [
        KlineData(
            date=k.date,
            open=k.open,
            high=k.high,
            low=k.low,
            close=k.close,
            volume=k.volume,
            amount=k.amount,
            change_pct=k.change_pct,
        )
        for k in klines_db
    ]
    klines.reverse()  # 升序排列

    # 计算指标
    from analysis import IndicatorCalculator
    calculator = IndicatorCalculator()
    indicators = calculator.calculate_all(klines)

    return {
        "symbol": symbol,
        "name": klines_db[0].name,
        "indicators": [
            {
                "date": str(ind.date),
                "ma5": ind.ma5,
                "ma20": ind.ma20,
                "rsi6": ind.rsi6,
                "macd_hist": ind.macd_hist,
                "k": ind.k,
                "d": ind.d,
                "j": ind.j,
            }
            for ind in indicators
        ],
    }


@router.get("/{symbol}/anomalies", response_model=dict)
def detect_anomalies(
    symbol: str,
    days: int = Query(60, ge=10, le=500),
    min_severity: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    检测股票异常

    - **symbol**: 股票代码
    - **days**: 检测天数
    - **min_severity**: 最低严重程度（low/medium/high/critical）
    """
    stock_service = StockService(db)
    klines_db = stock_service.get_klines(symbol, limit=days)

    if not klines_db:
        raise HTTPException(status_code=404, detail=f"未找到股票 {symbol} 的数据")

    # 转换为 KlineData
    klines = [
        KlineData(
            date=k.date,
            open=k.open,
            high=k.high,
            low=k.low,
            close=k.close,
            volume=k.volume,
        )
        for k in klines_db
    ]
    klines.reverse()

    # 执行分析
    service = AnalysisService()
    result = service.analyze(klines, symbol=symbol, detect_anomalies=True)

    return {
        "symbol": symbol,
        "name": klines_db[0].name,
        "total_klines": len(klines),
        "anomalies": [
            {
                "date": str(a.date),
                "type": a.anomaly_type.value,
                "severity": a.severity.value,
                "score": a.score,
                "description": a.description,
            }
            for a in result["anomalies"]
            if min_severity is None or a.severity.value in ["high", "critical"]
        ],
        "summary": result["report"].summary if result["report"] else {},
    }


@router.post("/{symbol}/analyze", response_model=dict)
def analyze_stock(
    symbol: str,
    days: int = Query(60, ge=10, le=500),
    db: Session = Depends(get_db),
):
    """完整分析（指标 + 异常检测）"""
    stock_service = StockService(db)
    klines_db = stock_service.get_klines(symbol, limit=days)

    if not klines_db:
        raise HTTPException(status_code=404, detail=f"未找到股票 {symbol} 的数据")

    klines = [
        KlineData(
            date=k.date,
            open=k.open,
            high=k.high,
            low=k.low,
            close=k.close,
            volume=k.volume,
        )
        for k in klines_db
    ]
    klines.reverse()

    service = AnalysisService()
    result = service.analyze(klines, symbol=symbol)

    return {
        "symbol": symbol,
        "indicators_count": len(result["indicators"]),
        "anomalies_count": len(result["anomalies"]),
        "report": result["report"],
    }
```

---

## 9. 调用示例

### 9.1 HTTP API 调用

```python
import httpx

# 获取技术指标
async with httpx.AsyncClient() as client:
    r = await client.get("http://localhost:8000/api/v1/analysis/000001/indicators?days=60")
    indicators = r.json()

# 检测异常
    r = await client.get("http://localhost:8000/api/v1/analysis/000001/anomalies?days=60")
    anomalies = r.json()
```

### 9.2 直接模块调用（Graph Agent）

```python
from data.services import StockService
from analysis import AnalysisService, KlineData

# 获取数据
with get_db_session() as session:
    stock_service = StockService(session)
    klines_db = stock_service.get_klines("000001", limit=60)

# 转换为 KlineData
klines = [KlineData(...) for k in klines_db]

# 执行分析
service = AnalysisService()
result = service.analyze(klines, symbol="000001")

# 分析结果
print(f"发现 {len(result['anomalies'])} 个异常")
for anomaly in result["anomalies"]:
    print(f"  {anomaly.date}: {anomaly.description}")
```

---

## 10. 依赖

```txt
# requirements.txt
pandas>=2.0.0
pandas-ta>=0.3.0
numpy>=1.24.0
```

---

## 11. 开发计划

| 阶段 | 内容 | 优先级 |
|------|------|--------|
| **Phase 1** | 数据模型 + 指标计算器 | P0 |
| **Phase 2** | 单指标检测器（RSI, MACD, BOLL, KDJ, ZScore） | P0 |
| **Phase 3** | 多指标组合检测 | P1 |
| **Phase 4** | API 接口开发 | P1 |
| **Phase 5** | 归因分析（未来） | P2 |

---

## 12. 需要补充的文件

> 以下文件在目录结构中提到，但需要在实现阶段创建

| 文件 | 说明 | 状态 |
|------|------|------|
| `analysis/interfaces/__init__.py` | 接口模块入口 | 待创建 |
| `analysis/interfaces/detector.py` | DetectorProtocol 定义 | 待创建 |
| `analysis/detectors/__init__.py` | 检测器模块入口 | 待创建 |
| `analysis/detectors/rsi_detector.py` | RSI 检测器 | 待创建 |
| `analysis/detectors/macd_detector.py` | MACD 检测器 | 待创建 |
| `analysis/detectors/boll_detector.py` | BOLL 检测器 | 待创建 |
| `analysis/detectors/kdj_detector.py` | KDJ 检测器 | 待创建 |
| `analysis/detectors/zscore_detector.py` | ZScore 检测器 | 待创建 |
| `analysis/services/__init__.py` | 服务模块入口 | 待创建 |
| `analysis/services/detector_service.py` | 检测器服务 | 待创建 |
| `analysis/services/analysis_service.py` | 分析服务 | 待创建 |
| `app/schemas.py` | API 响应模型 | 待创建 |
| `app/api/v1/analysis.py` | API 路由 | 待创建 |

---

## 13. 相关文档

- [技术指标说明](./技术指标.md)
- [数据采集模块](./data/)
- [系统架构](../architecture.md)
