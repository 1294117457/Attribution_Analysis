# Step 2: Core 模块配置

## 1. 目录结构

```
backend/
├── core/
│   ├── __init__.py
│   ├── config.py
│   └── types.py
```

---

## 2. 创建 core 模块

### 2.1 core/__init__.py

```python
"""Core 模块 - 全局配置和类型"""

from core.config import Settings, get_settings
from core.types import MarketType, AnomalyType

__all__ = [
    "Settings",
    "get_settings",
    "MarketType",
    "AnomalyType",
]
```

### 2.2 core/config.py

```python
"""全局配置管理"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # 数据库
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/attribution"
    DATABASE_URL_ASYNC: str = "postgresql+asyncpg://postgres:password@localhost:5432/attribution"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # API
    API_V1_PREFIX: str = "/api/v1"


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
```

### 2.3 core/types.py

```python
"""基础枚举类型"""

from enum import Enum


class MarketType(str, Enum):
    """市场类型"""
    SH = "sh"  # 上海
    SZ = "sz"  # 深圳
    BJ = "bj"  # 北京


class AnomalyType(str, Enum):
    """异常类型"""
    PRICE_SPIKE = "price_spike"       # 价格突刺
    PRICE_DROP = "price_drop"         # 价格暴跌
    VOLUME_SPIKE = "volume_spike"     # 成交量突刺
    VOLATILITY = "volatility"         # 波动率异常
    ZSCORE = "zscore"                 # Z-Score 异常


class SentimentType(str, Enum):
    """情感类型"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class CollectStatus(str, Enum):
    """采集状态"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
```

---

## 3. 验证

```python
# test_core.py
from core import get_settings, MarketType, AnomalyType

# 测试配置
settings = get_settings()
print(f"DATABASE_URL: {settings.DATABASE_URL}")

# 测试枚举
print(f"MarketType.SH: {MarketType.SH}")
print(f"AnomalyType.PRICE_SPIKE: {AnomalyType.PRICE_SPIKE}")

print("✅ Core 模块配置成功!")
```

---

## 4. 目录结构确认

```
backend/
├── core/
│   ├── __init__.py    ← 创建
│   ├── config.py      ← 创建
│   └── types.py       ← 创建
├── app/
└── ...
```
