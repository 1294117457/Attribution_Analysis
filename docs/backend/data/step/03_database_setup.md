# Step 3: 数据库配置

## 1. 目录结构

```
backend/
├── app/
│   ├── database/           # 数据库相关
│   │   ├── __init__.py
│   │   ├── base.py        # SQLAlchemy Base
│   │   ├── connection.py  # 连接管理
│   │   └── models/        # ORM 模型
│   │       ├── __init__.py
│   │       ├── mixins.py  # 混入类 (TimestampMixin)
│   │       └── stock.py   # 股票模型
│   │
│   ├── schemas/            # Pydantic 业务模型
│   │   ├── __init__.py
│   │   └── anomaly.py     # 异常相关模型
│   │
│   └── ...
```

### 命名规范

| 目录 | 类型 | 说明 |
|------|------|------|
| `database/` | SQLAlchemy | ORM 模型、数据库连接 |
| `database/models/` | ORM | 数据库表映射 |
| `schemas/` | Pydantic | 请求/响应模型 |

---

## 2. 创建数据库模块

### 2.1 app/database/base.py

```python
"""SQLAlchemy 基础类"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy 基础类"""
    pass
```

### 2.2 app/database/connection.py

```python
"""数据库连接管理"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from core.config import get_settings

settings = get_settings()

# 创建同步引擎
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Session 工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


@contextmanager
def get_db() -> Session:
    """获取数据库会话上下文管理器"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## 3. 创建 ORM 模型

### 3.1 app/database/models/mixins.py

```python
"""数据库模型混入类"""

from sqlalchemy import Column, DateTime
from datetime import datetime


class TimestampMixin:
    """时间戳混入"""

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
```

### 3.2 app/database/models/stock.py

```python
"""股票数据 ORM 模型"""

from sqlalchemy import Column, String, Float, Integer, Date, Index
from app.database.base import Base
from app.database.models.mixins import TimestampMixin


class StockKlineDB(Base, TimestampMixin):
    """K 线数据 ORM 模型"""

    __tablename__ = "stock_klines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, index=True)
    name = Column(String(50), nullable=True)
    date = Column(Date, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    change_pct = Column(Float, nullable=True)  # 涨跌幅 %

    # 复合唯一索引
    __table_args__ = (
        Index("idx_symbol_date", "symbol", "date", unique=True),
    )

    def __repr__(self):
        return f"<StockKlineDB {self.symbol} {self.date} close={self.close}>"
```

### 3.3 app/database/models/__init__.py

```python
"""ORM 模型"""

from app.database.models.mixins import TimestampMixin
from app.database.models.stock import StockKlineDB

__all__ = ["TimestampMixin", "StockKlineDB"]
```

---

## 4. 创建 Pydantic 业务模型

### 4.1 app/schemas/anomaly.py

```python
"""异常业务模型 (Pydantic)"""

from pydantic import BaseModel, Field
from datetime import date
from core.types import AnomalyType


class AnomalyCreate(BaseModel):
    """创建异常请求"""
    symbol: str
    date: date
    type: AnomalyType
    value: float
    threshold: float
    score: float = Field(..., ge=0, le=1)
    description: str | None = None


class AnomalyResponse(BaseModel):
    """异常响应"""
    id: int
    symbol: str
    date: date
    type: AnomalyType
    value: float
    threshold: float
    score: float
    description: str | None

    class Config:
        from_attributes = True  # 支持从 ORM 模型转换


class AnomalyListResponse(BaseModel):
    """异常列表响应"""
    total: int
    items: list[AnomalyResponse]
```

### 4.2 app/schemas/__init__.py

```python
"""Pydantic 业务模型"""

from app.schemas.anomaly import (
    AnomalyCreate,
    AnomalyResponse,
    AnomalyListResponse,
)

__all__ = [
    "AnomalyCreate",
    "AnomalyResponse",
    "AnomalyListResponse",
]
```

---

## 5. 更新 main.py

### app/main.py

```python
"""FastAPI 应用入口"""

from fastapi import FastAPI
from app.api.router import api_router
from app.database.base import Base
from app.database.connection import engine

app = FastAPI(
    title="智能金融数据归因分析平台",
    version="1.0.0",
)

# 注册路由
app.include_router(api_router)


@app.on_event("startup")
def on_startup():
    """启动时创建数据库表"""
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "ok"}
```

---

## 6. 验证数据库连接

```python
# test_db.py
from app.database.connection import engine, SessionLocal
from app.database.models.stock import StockKlineDB

# 测试连接
with engine.connect() as conn:
    result = conn.execute("SELECT 1")
    print("✅ 数据库连接成功!")

# 测试 Session
session = SessionLocal()
print("✅ Session 创建成功!")
session.close()

# 测试模型
from app.database.base import Base
print(f"StockKlineDB 表名: {StockKlineDB.__tablename__}")
```

运行:
```bash
python test_db.py
```

---

## 7. ORM vs Pydantic 对比

| 特性 | ORM 模型 | Pydantic 模型 |
|------|----------|---------------|
| 位置 | `database/models/` | `schemas/` |
| 用途 | 数据库表映射 | 请求/响应 |
| 基类 | `Base` (DeclarativeBase) | `BaseModel` |
| 字段类型 | `Column(...)` | 类型标注 |
| 示例 | `StockKlineDB` | `AnomalyCreate` |

### 数据流转

```
请求 JSON → AnomalyCreate (Pydantic) → AnomalyDB (ORM) → 数据库
数据库 → AnomalyDB (ORM) → AnomalyResponse (Pydantic) → 响应 JSON
```

---

## 8. 常见问题

### Q: 数据库连接失败？

检查:
1. PostgreSQL 服务是否运行
2. 数据库地址是否正确
3. 用户名密码是否正确
4. 数据库是否存在

### Q: 表已存在报错？

```python
# 使用 checkfirst=True 避免报错
Base.metadata.create_all(bind=engine, checkfirst=True)
```

### Q: 字段名写错？

SQLAlchemy 2.0 使用 `mapped_column`:
```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

class StockKlineDB(Base):
    __tablename__ = "stock_klines"

    symbol: Mapped[str] = mapped_column(String(10), index=True)
```
