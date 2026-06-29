# App 模块开发步骤

## 概述

`app` 是 FastAPI 应用层，负责：
- API 接口定义
- 数据库 ORM 模型
- 业务服务封装
- 依赖注入

---

## 开发步骤

### Step 1: 创建目录结构

```
backend/app/
├── __init__.py
├── main.py                    # FastAPI 入口
├── config.py                  # app 配置
├── dependencies.py            # 依赖注入
│
├── api/
│   ├── __init__.py
│   ├── router.py             # 路由汇总
│   ├── health.py             # /health
│   ├── stocks.py             # /stocks
│   ├── anomalies.py          # /anomalies
│   └── analysis.py            # /analysis
│
├── models/                   # API DTO
│   ├── __init__.py
│   ├── stock.py
│   ├── anomaly.py
│   └── analysis.py
│
├── database/
│   ├── __init__.py
│   ├── connection.py         # 数据库连接
│   └── models/
│       ├── __init__.py
│       ├── base.py           # SQLAlchemy Base
│       ├── stock_db.py       # 股票 ORM
│       └── anomaly_db.py     # 异常 ORM
│
└── services/
    ├── __init__.py
    ├── stock_service.py      # 股票服务
    └── anomaly_service.py    # 异常服务
```

### Step 2: 数据库连接 (`database/connection.py`)

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from core.config import get_settings

settings = get_settings()

# 同步引擎
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Session 工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db() -> Session:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Step 3: ORM 基础类 (`database/models/base.py`)

```python
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import DateTime
from datetime import datetime

class Base(DeclarativeBase):
    """SQLAlchemy 基础类"""
    pass

class TimestampMixin:
    """时间戳混入"""
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Step 4: ORM 模型 (`database/models/stock_db.py`)

```python
from sqlalchemy import Column, String, Float, Integer, Date, Index
from app.database.models.base import Base, TimestampMixin

class StockKlineDB(Base, TimestampMixin):
    """K线数据 ORM"""
    __tablename__ = "stock_klines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, index=True)
    date = Column(Date, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    change_pct = Column(Float, nullable=True)

    __table_args__ = (
        Index("idx_symbol_date", "symbol", "date", unique=True),
    )
```

### Step 5: API DTO 模型 (`models/anomaly.py`)

```python
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

### Step 6: 业务服务 (`services/anomaly_service.py`)

```python
from sqlalchemy.orm import Session
from typing import list
from app.database.models.anomaly_db import AnomalyDB
from app.models.anomaly import AnomalyCreate, AnomalyResponse
from core.models.anomaly import AnomalyRecord

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

    def to_record(self, response: AnomalyResponse) -> AnomalyRecord:
        """转换为核心领域模型"""
        return AnomalyRecord(
            id=str(response.id),
            symbol=response.symbol,
            date=response.date,
            type=response.type,
            value=response.value,
            threshold=response.threshold,
            score=response.score,
            description=response.description,
        )
```

### Step 7: API 路由 (`api/anomalies.py`)

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.anomaly_service import AnomalyService
from app.models.anomaly import (
    AnomalyCreate,
    AnomalyResponse,
    AnomalyListResponse,
)
from datetime import date

router = APIRouter(prefix="/anomalies", tags=["异常"])

@router.post("", response_model=AnomalyResponse)
def create_anomaly(
    data: AnomalyCreate,
    db: Session = Depends(get_db),
):
    """创建异常记录"""
    service = AnomalyService(db)
    return service.create(data)

@router.get("/stock/{symbol}", response_model=AnomalyListResponse)
def list_anomalies(
    symbol: str,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: Session = Depends(get_db),
):
    """查询股票的异常记录"""
    service = AnomalyService(db)
    items = service.list_by_symbol(symbol, start_date, end_date)
    return AnomalyListResponse(total=len(items), items=items)
```

### Step 8: FastAPI 入口 (`main.py`)

```python
from fastapi import FastAPI
from app.api.router import api_router
from app.database.connection import engine
from app.database.models.base import Base

app = FastAPI(
    title="智能金融数据归因分析平台",
    version="1.0.0",
)

# 注册路由
app.include_router(api_router)

@app.on_event("startup")
def on_startup():
    """启动时创建表"""
    Base.metadata.create_all(bind=engine)
```

### Step 9: 路由汇总 (`api/router.py`)

```python
from fastapi import APIRouter
from app.api import health, stocks, anomalies, analysis

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(stocks.router)
api_router.include_router(anomalies.router)
api_router.include_router(analysis.router)
```

### Step 10: 依赖注入 (`dependencies.py`)

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.anomaly_service import AnomalyService
from app.services.stock_service import StockService

def get_anomaly_service(db: Session = Depends(get_db)) -> AnomalyService:
    return AnomalyService(db)

def get_stock_service(db: Session = Depends(get_db)) -> StockService:
    return StockService(db)
```

---

## 验证清单

- [ ] `app/main.py` - FastAPI 能正常启动
- [ ] `/health` - 健康检查接口返回正常
- [ ] `/anomalies` POST - 能创建异常记录
- [ ] `/anomalies/stock/{symbol}` GET - 能查询异常列表
- [ ] 数据库表自动创建成功
- [ ] API 响应格式正确

---

## 目录结构汇总

```
app/
├── __init__.py
├── main.py
├── config.py
├── dependencies.py
│
├── api/
│   ├── __init__.py
│   ├── router.py
│   ├── health.py
│   ├── stocks.py
│   ├── anomalies.py
│   └── analysis.py
│
├── models/
│   ├── __init__.py
│   ├── stock.py
│   ├── anomaly.py
│   └── analysis.py
│
├── database/
│   ├── __init__.py
│   ├── connection.py
│   └── models/
│       ├── __init__.py
│       ├── base.py
│       ├── stock_db.py
│       └── anomaly_db.py
│
└── services/
    ├── __init__.py
    ├── stock_service.py
    └── anomaly_service.py
```
