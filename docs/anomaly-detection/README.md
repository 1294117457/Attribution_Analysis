# 异常检测设计文档

**版本**：v1.0  
**日期**：2026年6月  
**目标**：基于A股K线数据，实现价格/成交量异常检测

---

## 一、异常检测目标

### 1.1 解决的问题

| 问题 | 描述 |
|------|------|
| **价格异常** | 股价单日暴涨/暴跌超阈值 |
| **成交量异常** | 放量/缩量超平时水平 |
| **趋势异常** | 均线排列破坏、趋势反转信号 |
| **波动异常** | 日内振幅过大/过小 |

### 1.2 异常检测的价值

```
K线数据 → 异常检测 → 发现异常点 → 触发归因分析 → 生成报告
```

**为什么先做异常检测？**
- 不是每天都需要分析，异常点是关键
- 减少无效分析，聚焦真正重要的时刻
- 为归因分析提供"分析什么"的前提

---

## 二、异常检测技术方案

### 2.1 检测维度

| 维度 | 检测目标 | 通俗理解 |
|------|----------|----------|
| **价格维度** | 涨跌幅异常 | 涨/跌得太猛了 |
| **量能维度** | 成交量异常 | 交易太活跃/冷清 |
| **波动维度** | 振幅异常 | 今天波动大/小得不正常 |
| **趋势维度** | 均线破坏 | 跌破重要均线 |

### 2.2 检测算法

#### 2.2.1 基础统计方法

| 算法 | 原理 | 适用场景 |
|------|------|----------|
| **Z-Score** | 数据偏离均值超过N个标准差 | 价格/成交量异常 |
| **IQR（四分位距）** | 超出 Q1-1.5*IQR ~ Q3+1.5*IQR 范围 | 稳健的异常检测 |
| **移动平均偏离** | 当前值偏离MA的程度 | 趋势异常 |

#### 2.2.2 方向检测方法

| 算法 | 原理 | 适用场景 |
|------|------|----------|
| **涨停/跌停检测** | 涨跌幅达到±10%或±20% | 极端行情 |
| **连续涨跌检测** | 连续N天上涨/下跌 | 趋势跟踪 |
| **突破检测** | 价格突破布林带上下轨 | 突破信号 |

#### 2.2.3 速度/加速度检测

| 算法 | 原理 | 适用场景 |
|------|------|----------|
| **涨速检测** | 单位时间内价格变化率 | 盘中监控 |
| **放量速度** | 成交量变化率 | 资金异动 |

### 2.3 技术指标辅助

异常检测需要配合技术指标来判断：

| 指标 | 作用 |
|------|------|
| **MA5/MA20** | 判断价格相对均线位置 |
| **MACD** | 判断趋势强度、背离 |
| **KDJ** | 超买超卖信号 |
| **布林带** | 判断价格是否"离谱" |
| **RSI** | 相对强弱，超买>70，超卖<30 |

---

## 三、工程结构设计

### 3.1 模块划分

```
backend/app/
├── services/
│   └── detectors/              # 异常检测服务
│       ├── __init__.py
│       ├── base.py             # 检测器基类
│       ├── price_detector.py   # 价格异常检测
│       ├── volume_detector.py  # 成交量异常检测
│       ├── volatility_detector.py  # 波动异常检测
│       └── trend_detector.py   # 趋势异常检测
│
├── models/
│   └── kline.py               # K线数据模型（dict结构）
│
├── api/
│   └── v1/
│       └── detectors.py        # 检测API接口
│
└── schemas/
    └── detector.py             # 请求/响应schema
```

### 3.2 核心类设计

#### 3.2.1 检测器基类

```python
# 伪代码，不含实际实现
class BaseDetector:
    """所有检测器的基类"""
    
    name: str           # 检测器名称
    threshold: float    # 阈值
    
    def detect(self, kline: dict, history: list[dict]) -> DetectionResult:
        """检测单条K线"""
        raise NotImplementedError
    
    def batch_detect(self, klines: list[dict]) -> list[DetectionResult]:
        """批量检测多条K线"""
        raise NotImplementedError
```

#### 3.2.2 检测结果模型

```python
# 伪代码
@dataclass
class DetectionResult:
    is_anomaly: bool           # 是否异常
    detector_name: str         # 哪个检测器检出
    severity: str              # 严重程度: low/medium/high/critical
    score: float               # 置信度 0-1
    details: dict              # 详细数据
    reason: str                # 原因描述
```

### 3.3 数据流转

```
输入数据
    │
    ▼
┌─────────────────┐
│ 单只股票K线     │  当前K线 + 历史K线(30天)
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 技术指标计算    │  计算MA5/MA20/MACD等
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 多种检测器并行  │  价格/成交量/波动/趋势
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 结果聚合        │  综合判断是否异常
└─────────────────┘
    │
    ▼
输出
    ├── 检测结果列表
    ├── 异常等级
    └── 触发原因
```

---

## 四、功能实现方案

### 4.1 检测流程

```
用户请求：检测茅台 2026-06-26 是否异常
    │
    ▼
Step 1: 获取K线数据
    - 当前K线：6/26的开高低收
    - 历史K线：6/1-6/25的数据（计算指标用）
    │
    ▼
Step 2: 计算技术指标
    - MA5 = 近5日收盘均价
    - MA20 = 近20日收盘均价
    - MACD = (EMA12-EMA26)信号线
    - 布林带 = MA20 ± 2*标准差
    │
    ▼
Step 3: 多种检测器并行检测
    ┌─────────────────────────────────┐
    │ ZScoreDetector: 价格偏离程度    │
    │ IQRDetector: 成交量异常         │
    │ DirectionDetector: 涨跌停检测   │
    │ VolatilityDetector: 振幅异常    │
    │ TrendDetector: 均线破坏检测     │
    └─────────────────────────────────┘
    │
    ▼
Step 4: 结果聚合
    - 统计有多少检测器报告异常
    - 计算综合异常分数
    - 生成异常原因描述
    │
    ▼
返回结果
    {
        "is_anomaly": true,
        "severity": "high",
        "score": 0.85,
        "triggers": ["价格跌破MA20", "成交量放大2倍"],
        "details": {...}
    }
```

### 4.2 检测器详细设计

#### 4.2.1 价格异常检测（ZScore）

| 参数 | 说明 | 默认值 |
|------|------|--------|
| threshold | 标准差倍数 | 2.5 |
| lookback_days | 回看天数 | 30 |

**判断逻辑**：
- 计算近30天收盘价的均值和标准差
- 当前价格偏离均值 > threshold × 标准差 → 异常

#### 4.2.2 成交量异常检测（IQR）

| 参数 | 说明 | 默认值 |
|------|------|--------|
| k | IQR倍数 | 1.5 |

**判断逻辑**：
- 计算 Q1（25%分位）和 Q3（75%分位）
- 超出 [Q1 - k×IQR, Q3 + k×IQR] → 异常

#### 4.2.3 涨跌停检测

| 参数 | 说明 |
|------|------|
| 主板阈值 | ±10% |
| 创业板/科创板 | ±20% |

**判断逻辑**：
- 涨跌幅达到阈值 → 触发涨停/跌停异常

#### 4.2.4 趋势异常检测

| 检测项 | 判断逻辑 |
|--------|----------|
| 均线多头排列破坏 | MA5 < MA20 且前一天 MA5 > MA20 |
| 均线空头排列破坏 | MA5 > MA20 且前一天 MA5 < MA20 |
| 跌破重要均线 | 收盘价 < MA20 |
| 突破布林带上轨 | 收盘价 > BOLL_upper |

### 4.3 结果聚合策略

```python
# 伪代码
def aggregate_results(detections: list[DetectionResult]) -> AggregatedResult:
    """
    聚合多个检测器的结果
    """
    # 1. 统计异常数量
    anomaly_count = sum(1 for d in detections if d.is_anomaly)
    
    # 2. 计算综合分数（加权平均）
    weights = {"ZScore": 0.3, "IQR": 0.2, "Direction": 0.3, "Trend": 0.2}
    total_score = sum(
        d.score * weights.get(d.detector_name, 0.25)
        for d in detections if d.is_anomaly
    )
    
    # 3. 判断严重程度
    if anomaly_count >= 3:
        severity = "high"
    elif anomaly_count == 2:
        severity = "medium"
    elif anomaly_count == 1:
        severity = "low"
    else:
        severity = "normal"
    
    return AggregatedResult(
        is_anomaly=anomaly_count > 0,
        severity=severity,
        score=total_score,
        triggers=[d.reason for d in detections if d.is_anomaly]
    )
```

---

## 五、API接口设计

### 5.1 检测接口

```
POST /api/v1/detectors/detect

请求体：
{
    "symbol": "600519",        # 股票代码
    "trade_date": "2026-06-26" # 检测日期
}

响应：
{
    "symbol": "600519",
    "trade_date": "2026-06-26",
    "is_anomaly": true,
    "severity": "high",
    "score": 0.85,
    "triggers": [
        {"detector": "ZScore", "reason": "价格偏离均值2.8个标准差"},
        {"detector": "IQR", "reason": "成交量超过Q3+1.5*IQR"},
        {"detector": "Trend", "reason": "收盘价跌破MA20"}
    ],
    "kline": {
        "open": 1850.0,
        "high": 1880.0,
        "low": 1840.0,
        "close": 1870.0,
        "volume": 5000000.0,
        "change_pct": 1.08
    }
}
```

### 5.2 批量检测接口

```
POST /api/v1/detectors/batch-detect

请求体：
{
    "symbols": ["600519", "000858", "600036"],
    "trade_date": "2026-06-26"
}

响应：
{
    "results": [
        {"symbol": "600519", "is_anomaly": true, "severity": "high"},
        {"symbol": "000858", "is_anomaly": false, "severity": "normal"},
        {"symbol": "600036", "is_anomaly": true, "severity": "medium"}
    ],
    "total": 3,
    "anomaly_count": 2
}
```

---

## 六、配置管理

### 6.1 检测器配置

```python
# backend/app/config/detector_config.py

DETECTOR_SETTINGS = {
    "zscore": {
        "enabled": True,
        "threshold": 2.5,
        "lookback_days": 30,
        "weight": 0.3
    },
    "iqr": {
        "enabled": True,
        "k": 1.5,
        "lookback_days": 30,
        "weight": 0.2
    },
    "direction": {
        "enabled": True,
        "limit_up_threshold": 10.0,  # 主板
        "limit_down_threshold": -10.0,
        "weight": 0.3
    },
    "trend": {
        "enabled": True,
        "ma_periods": [5, 20, 60],
        "boll_period": 20,
        "boll_std": 2,
        "weight": 0.2
    }
}

# 异常等级阈值
SEVERITY_THRESHOLDS = {
    "critical": 0.95,  # score >= 0.95
    "high": 0.7,       # score >= 0.7
    "medium": 0.4,     # score >= 0.4
    "low": 0.0         # score > 0
}
```

---

## 七、后续扩展方向

### 7.1 短期扩展（1-2周）

| 功能 | 说明 |
|------|------|
| 实时监控 | 盘中分时数据异常检测 |
| 板块联动 | 检测同板块多只股票同时异常 |
| 邮件/钉钉通知 | 异常发生时主动推送 |

### 7.2 中期扩展（1-2月）

| 功能 | 说明 |
|------|------|
| AI辅助判断 | LLM综合算法结果，给出最终判断 |
| 归因分析联动 | 异常检测触发归因分析 |
| 历史回测 | 评估检测器准确率 |

### 7.3 长期扩展

| 功能 | 说明 |
|------|------|
| 机器学习模型 | 基于历史数据训练预测模型 |
| 自动交易 | 异常信号触发交易策略 |

---

## 八、相关文档

- [系统架构](../architecture.md) - 整体技术架构
- [数据采集](../data/caiji.md) - AkShare数据获取
- [API文档](../api.md) - 接口详细定义
