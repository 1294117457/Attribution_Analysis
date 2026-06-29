# Core 模块设计分析

## 1. 模块定位

```
┌─────────────────────────────────────────────────────────────────┐
│                         其他模块                                  │
│     app/    data/    ml/    rag/    graph/                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         core/ (共享层)                           │
│                                                                 │
│   config.py ──────▶ 全局配置管理                                 │
│   types.py ──────▶ 枚举/常量定义                                │
│   models/ ───────▶ 核心领域模型                                 │
│                                                                 │
│   stock.py ──────▶ 股票数据                                     │
│   anomaly.py ────▶ 异常检测                                     │
│   attribution.py ─▶ 归因分析                                     │
└─────────────────────────────────────────────────────────────────┘
```

## 2. 设计原则

### 2.1 单一职责

| 文件 | 职责 |
|------|------|
| `config.py` | 仅负责配置加载，不含业务逻辑 |
| `types.py` | 仅定义枚举和常量 |
| `models/*.py` | 仅定义数据结构 |

### 2.2 稳定优先

core 模块应该是最稳定的代码：
- **不依赖** 其他业务模块
- **不包含** 数据库操作
- **不包含** API 定义

### 2.3 类型完整性

所有跨模块传递的数据对象必须先在 core 中定义。

## 3. 模型设计详解

### 3.1 股票模型 (stock.py)

```
StockBase (基础信息)
    │
    ├── symbol: str      # 股票代码，格式: 000001
    ├── name: str        # 股票名称
    └── market: MarketType  # 市场 (sh/sz/bj)
    │
    ▼
StockKline (+ K线数据)
    │
    ├── date: date
    ├── open/high/low/close: float
    ├── volume: int
    ├── amount: float
    └── change_pct: float  # 涨跌幅
    │
    ▼
StockWithIndicators (+ 技术指标)
    │
    ├── ma5/ma10/ma20: float  # 均线
    ├── rsi: float            # RSI
    ├── macd/macd_signal/macd_hist: float  # MACD
    └── boll_upper/middle/lower: float  # 布林带
```

**设计理由**：
- 使用继承链保持字段清晰
- `change_pct` 可选，因为新数据可能未计算
- 技术指标放在扩展模型，不污染基础数据

### 3.2 异常模型 (anomaly.py)

```
AnomalyRecord (异常记录)
    │
    ├── id: str           # 唯一标识
    ├── symbol: str       # 关联股票
    ├── date: date        # 发生日期
    ├── type: AnomalyType # 异常类型
    │
    ├── value: float      # 实际值
    ├── threshold: float  # 阈值
    ├── score: float      # 异常分数 (0-1)
    │
    └── description: str  # 异常描述

AnomalyDetectRequest (检测请求)
    │
    ├── symbol: str
    ├── start_date: date
    ├── end_date: date
    └── methods: list[AnomalyType]  # 使用的检测方法

AnomalyDetectResult (检测结果)
    │
    ├── symbol: str
    ├── anomalies: list[AnomalyRecord]  # 所有异常
    └── summary: str                    # 摘要文本
```

**设计理由**：
- 分离请求/结果模型，便于 API 层使用
- `score` 归一化到 0-1，便于后续排序和筛选
- 支持多种检测方法并存

### 3.3 归因模型 (attribution.py)

```
AttributionFactor (归因因子)
    │
    ├── name: str        # 因子名称
    ├── weight: float    # 权重 (0-1)
    ├── score: float     # 得分
    └── description: str # 说明

AttributionResult (归因结果)
    │
    ├── symbol: str
    ├── date: date
    ├── anomaly: AnomalyRecord  # 关联的异常
    │
    ├── market_factor: AttributionFactor   # 市场因素
    ├── industry_factor: AttributionFactor # 行业因素
    ├── company_factor: AttributionFactor  # 公司因素
    ├── news_factor: AttributionFactor    # 新闻因素
    │
    ├── conclusion: str   # 综合结论
    └── confidence: float  # 置信度 (0-1)
```

**设计理由**：
- 因子化设计便于 LLM 理解和修改
- 所有因子结构一致，支持动态增减
- `conclusion` 由 LLM 生成，自由度高

## 4. 类型系统设计

### 4.1 AnomalyType 枚举

```python
class AnomalyType(str, Enum):
    ZSCORE = "zscore"              # 统计方法：Z-Score
    IQR = "iqr"                   # 统计方法：四分位距
    VOLATILITY = "volatility"     # 波动率检测
    ISOLATION_FOREST = "isolation_forest"  # 机器学习方法
```

**设计理由**：
- 继承 `str` 便于 JSON 序列化
- 后续可扩展更多检测方法

### 4.2 PhaseType 枚举

```python
class PhaseType(str, Enum):
    START = "start"
    DATA_COLLECT = "data_collect"
    ANOMALY_DETECT = "anomaly_detect"
    SENTIMENT_ANALYZE = "sentiment_analyze"
    ATTRIBUTION = "attribution"
    REPORT = "report"
    END = "end"
```

**设计理由**：
- 对应 LangGraph 的工作流阶段
- 便于日志追踪和问题定位

## 5. 配置管理设计

### 5.1 Settings 类

```python
class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    API_V1_PREFIX: str = "/api/v1"
    ML_MODEL_PATH: str = "./data/models"
    RAG_VECTOR_DIM: int = 1536
```

**设计理由**：
- 使用 `pydantic-settings` 自动加载 .env
- 提供默认值便于开发环境
- 生产环境通过环境变量覆盖

### 5.2 单例模式

```python
@lru_cache
def get_settings() -> Settings:
    return Settings()
```

**设计理由**：
- 避免重复解析 .env
- 应用启动时加载一次
- 全局可用

## 6. 扩展指南

### 6.1 添加新的领域模型

1. 在 `core/models/` 下创建新文件，如 `news.py`
2. 定义模型类，继承 `BaseModel`
3. 在 `core/models/__init__.py` 中导出
4. 在 `core/__init__.py` 中添加

### 6.2 添加新的枚举类型

1. 在 `core/types.py` 中添加
2. 考虑是否需要 str 继承（影响 JSON 序列化）

### 6.3 修改现有模型

⚠️ **注意**：
- core 是底层，影响范围大
- 添加可选字段相对安全
- 删除/修改字段需要评估影响
- 考虑版本兼容性

## 7. 测试策略

```python
# tests/test_core/test_models.py
def test_stock_kline_serialization():
    """测试股票K线模型序列化"""
    kline = StockKline(
        symbol="000001",
        name="平安银行",
        market=MarketType.SZ,
        date=date(2024, 1, 1),
        open=10.5,
        high=10.8,
        low=10.3,
        close=10.6,
        volume=1000000,
        amount=10500000.0,
    )
    data = kline.model_dump()
    assert data["symbol"] == "000001"
    assert data["market"] == "sz"

def test_anomaly_score_range():
    """测试异常分数范围"""
    anomaly = AnomalyRecord(score=0.95)
    assert 0 <= anomaly.score <= 1
```

## 8. 常见问题

### Q: 为什么不用 SQLAlchemy 模型放在 core？

**A**: SQLAlchemy 模型与数据库强耦合，不适合作为核心领域模型。
- core 应该与数据库无关
- 数据库模型放在 `app/database/models/`

### Q: Pydantic v1 和 v2 怎么选？

**A**: 使用 Pydantic v2：
```python
from pydantic import BaseModel, Field  # v2 方式
```
- v1 的 `BaseModel.schema()` → v2 的 `model_json_schema()`
- v1 的 `dict()` → v2 的 `model_dump()`

### Q: 如何处理 datetime 序列化？

**A**: Pydantic v2 默认处理：
```python
class Config:
    json_encoders = {datetime: lambda v: v.isoformat()}
```
或使用 `model_config = ConfigDict(json_encoders={...})`
