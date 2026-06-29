# Core 模块开发步骤

## 概述

`core` 是整个项目的核心共享层，定义全局配置、基础类型和核心领域模型。所有其他模块（app, data, ml, rag, graph）都依赖 core。

---

## 开发步骤

### Step 1: 创建目录结构

```
backend/core/
├── __init__.py
├── config.py
├── types.py
└── models/
    ├── __init__.py
    ├── stock.py
    ├── anomaly.py
    └── attribution.py
```

### Step 2: 定义基础配置 (`config.py`)

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """全局配置"""

    # 数据库
    DATABASE_URL: str
    DATABASE_URL_ASYNC: str

    # Redis
    REDIS_URL: str

    # API
    API_V1_PREFIX: str = "/api/v1"

    # ML
    ML_MODEL_PATH: str = "./data/models"

    # RAG
    RAG_VECTOR_DIM: int = 1536
    RAG_TOP_K: int = 5

    class Config:
        env_file = ".env"

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### Step 3: 定义基础类型 (`types.py`)

```python
from enum import Enum

class AnomalyType(str, Enum):
    """异常类型"""
    ZSCORE = "zscore"              # Z-Score 异常
    IQR = "iqr"                   # IQR 四分位异常
    VOLATILITY = "volatility"     # 波动率异常
    ISOLATION_FOREST = "isolation_forest"  # 隔离森林

class SentimentType(str, Enum):
    """情感类型"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

class MarketType(str, Enum):
    """市场类型"""
    SH = "sh"    # 上海
    SZ = "sz"    # 深圳
    BJ = "bj"    # 北京

class PhaseType(str, Enum):
    """分析阶段"""
    START = "start"
    DATA_COLLECT = "data_collect"
    ANOMALY_DETECT = "anomaly_detect"
    SENTIMENT_ANALYZE = "sentiment_analyze"
    ATTRIBUTION = "attribution"
    REPORT = "report"
    END = "end"
```

### Step 4: 定义核心领域模型

**`models/stock.py`** - 股票数据模型：

```python
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional
from core.types import MarketType

class StockBase(BaseModel):
    """股票基础模型"""
    symbol: str = Field(..., description="股票代码，如 000001")
    name: str = Field(..., description="股票名称")
    market: MarketType = Field(..., description="市场")

class StockKline(StockBase):
    """K线数据"""
    date: date
    open: float = Field(..., ge=0)
    high: float = Field(..., ge=0)
    low: float = Field(..., ge=0)
    close: float = Field(..., ge=0)
    volume: int = Field(..., ge=0)
    amount: float = Field(..., ge=0, description="成交额")
    change_pct: Optional[float] = Field(None, description="涨跌幅 %")

class StockWithIndicators(StockKline):
    """带技术指标的K线"""
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    boll_upper: Optional[float] = None
    boll_middle: Optional[float] = None
    boll_lower: Optional[float] = None
```

**`models/anomaly.py`** - 异常检测模型：

```python
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, Literal
from core.types import AnomalyType

class AnomalyBase(BaseModel):
    """异常基础模型"""
    id: Optional[str] = None
    symbol: str
    date: date
    type: AnomalyType

class AnomalyRecord(AnomalyBase):
    """异常记录"""
    value: float = Field(..., description="异常值")
    threshold: float = Field(..., description="阈值")
    score: float = Field(..., description="异常分数 0-1")
    description: Optional[str] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

class AnomalyDetectRequest(BaseModel):
    """异常检测请求"""
    symbol: str
    start_date: date
    end_date: date
    methods: list[AnomalyType] = [AnomalyType.ZSCORE]

class AnomalyDetectResult(BaseModel):
    """异常检测结果"""
    symbol: str
    anomalies: list[AnomalyRecord]
    summary: str = Field(..., description="异常摘要")
```

**`models/attribution.py`** - 归因分析模型：

```python
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional
from core.models.anomaly import AnomalyRecord

class AttributionFactor(BaseModel):
    """归因因子"""
    name: str = Field(..., description="因子名称")
    weight: float = Field(..., ge=0, le=1, description="权重 0-1")
    score: float = Field(..., description="得分")
    description: str = Field(..., description="说明")

class AttributionResult(BaseModel):
    """归因结果"""
    symbol: str
    date: date
    anomaly: AnomalyRecord

    # 归因因子
    market_factor: Optional[AttributionFactor] = None   # 市场因素
    industry_factor: Optional[AttributionFactor] = None  # 行业因素
    company_factor: Optional[AttributionFactor] = None   # 公司因素
    news_factor: Optional[AttributionFactor] = None     # 新闻因素

    # 综合结论
    conclusion: str = Field(..., description="归因结论")
    confidence: float = Field(..., ge=0, le=1, description="置信度")
```

### Step 5: 创建模块导出 (`__init__.py`)

```python
from core.config import Settings, get_settings
from core.types import (
    AnomalyType,
    SentimentType,
    MarketType,
    PhaseType,
)
from core.models import (
    StockKline,
    StockWithIndicators,
    AnomalyRecord,
    AnomalyDetectRequest,
    AnomalyDetectResult,
    AttributionResult,
    AttributionFactor,
)

__all__ = [
    "Settings",
    "get_settings",
    "AnomalyType",
    "SentimentType",
    "MarketType",
    "PhaseType",
    "StockKline",
    "StockWithIndicators",
    "AnomalyRecord",
    "AnomalyDetectRequest",
    "AnomalyDetectResult",
    "AttributionResult",
    "AttributionFactor",
]
```

---

## 验证清单

- [ ] `core/config.py` - 配置能正常加载 .env
- [ ] `core/types.py` - 所有枚举类型定义正确
- [ ] `core/models/stock.py` - StockKline 模型可序列化
- [ ] `core/models/anomaly.py` - 异常模型包含必要字段
- [ ] `core/models/attribution.py` - 归因模型结构完整
- [ ] 导入测试无循环依赖

---

## 依赖

```
# pyproject.toml
dependencies = [
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "python-dotenv>=1.0",
]
```
