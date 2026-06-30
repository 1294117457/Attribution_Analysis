# Step 4: App 模块

## 1. 目录结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── anomalies.py
│   │   └── health.py
│   │
│   ├── database/           # SQLAlchemy ORM
│   │   ├── __init__.py
│   │   ├── base.py        # Base = declarative_base()
│   │   ├── connection.py  # 连接管理
│   │   └── models/       # ORM 模型
│   │       ├── __init__.py
│   │       ├── mixins.py # TimestampMixin
│   │       └── stock.py  # StockKlineDB
│   │
│   ├── schemas/           # Pydantic 业务模型
│   │   ├── __init__.py
│   │   └── anomaly.py    # AnomalyCreate/Response
│   │
│   └── services/
│       ├── __init__.py
│       └── anomaly_service.py
```

---

## 2. 创建 API 模块

### 2.1 app/api/health.py

```python
"""健康检查 API"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    """健康检查"""
    return {"status": "ok", "version": "1.0.0"}


@router.get("/ping")
def ping():
    """Ping"""
    return "pong"
```

### 2.2 app/api/router.py

```python
"""路由汇总"""

from fastapi import APIRouter
from app.api import health, anomalies

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(anomalies.router)
```

### 2.3 app/api/__init__.py

```python
"""API 模块"""
```

---

## 3. 创建服务层

### 3.1 app/services/anomaly_service.py

```python
"""异常服务"""

from sqlalchemy import Column, String, Float, Integer, Date, Index
from sqlalchemy.orm import Session
from app.database.base import Base
from app.database.models.mixins import TimestampMixin
from app.schemas.anomaly import AnomalyCreate, AnomalyResponse


class AnomalyDB(Base, TimestampMixin):
    """异常数据 ORM 模型"""

    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, index=True)
    date = Column(Date, nullable=False)
    type = Column(String(50), nullable=False)
    value = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    score = Column(Float, nullable=False)
    description = Column(String(500), nullable=True)

    __table_args__ = (Index("idx_symbol_date", "symbol", "date"),)


class AnomalyService:
    """异常服务"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: AnomalyCreate) -> AnomalyResponse:
        """创建异常记录"""
        db_obj = AnomalyDB(**data.model_dump())
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return AnomalyResponse.model_validate(db_obj)

    def list_by_symbol(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[AnomalyResponse]:
        """查询股票的异常记录"""
        query = self.db.query(AnomalyDB).filter(AnomalyDB.symbol == symbol)

        if start_date:
            query = query.filter(AnomalyDB.date >= start_date)
        if end_date:
            query = query.filter(AnomalyDB.date <= end_date)

        return [AnomalyResponse.model_validate(r) for r in query.all()]
```

### 3.2 app/services/__init__.py

```python
"""服务模块"""
```

---

## 4. 创建 FastAPI 入口

### 4.1 app/main.py

```python
"""FastAPI 应用入口"""

from fastapi import FastAPI
from app.api.router import api_router
from app.database.base import Base
from app.database.connection import engine

app = FastAPI(
    title="智能金融数据归因分析平台",
    version="1.0.0",
    description="A股数据采集、异常检测、归因分析",
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
    return {"status": "ok", "version": "1.0.0"}
```

---

## 5. 验证 API

### 5.1 启动服务

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5.2 测试 API

```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# Ping
curl http://localhost:8000/api/v1/ping
```

### 5.3 访问 Swagger

```
http://localhost:8000/docs
```

---

## 6. 目录结构确认

```
app/
├── __init__.py
├── main.py           ← 创建
│
├── api/
│   ├── __init__.py
│   ├── router.py
│   ├── health.py     ← 新建
│   └── anomalies.py
│
├── database/
│   ├── __init__.py
│   ├── base.py
│   ├── connection.py
│   └── models/
│       ├── __init__.py
│       ├── mixins.py  ← 从 base.py 重命名
│       └── stock.py
│
├── schemas/           ← 从 models/ 重命名
│   ├── __init__.py
│   └── anomaly.py
│
└── services/
    ├── __init__.py
    └── anomaly_service.py
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
