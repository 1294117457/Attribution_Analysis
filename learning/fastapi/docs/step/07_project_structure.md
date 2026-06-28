# Step 07: 项目结构 - 工程化组织

## 学习目标
学习如何组织大型 FastAPI 项目的目录结构

## 概念速览

```
项目结构
├── app/
│   ├── __init__.py
│   ├── main.py           # 应用入口
│   ├── config.py         # 配置
│   ├── database.py       # 数据库连接
│   ├── api/              # API 路由
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── stocks.py # 股票相关 API
│   │       └── analysis.py # 分析 API
│   ├── models/           # 数据库模型
│   │   └── stock.py
│   ├── schemas/          # Pydantic 模型
│   │   └── stock.py
│   ├── services/         # 业务逻辑
│   │   └── stock_service.py
│   └── core/             # 核心功能
│       ├── security.py
│       └── exceptions.py
├── tests/                # 测试
├── requirements.txt
└── .env
```

## 任务

### 任务 1: 创建项目目录

```bash
# 在 learning/fastapi/ 下创建以下结构
mkdir -p demo_07_structure/app/api/v1
mkdir -p demo_07_structure/app/models
mkdir -p demo_07_structure/app/schemas
mkdir -p demo_07_structure/app/services
mkdir -p demo_07_structure/app/core
mkdir -p demo_07_structure/tests
```

### 任务 2: 配置文件

创建 `demo_07_structure/app/config.py`：

```python
"""应用配置"""
from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache

class Settings(BaseSettings):
    """应用设置"""
    
    # 应用信息
    APP_NAME: str = "股票分析 API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 数据库
    DATABASE_URL: str = "sqlite:///./stocks.db"
    
    # API 密钥
    API_KEY: str = "test-api-key"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # 配置
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """获取配置（单例）"""
    return Settings()
```

### 任务 3: 数据库配置

创建 `demo_07_structure/app/database.py`：

```python
"""数据库配置"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """数据库会话依赖"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """初始化数据库"""
    Base.metadata.create_all(bind=engine)
```

### 任务 4: 数据库模型

创建 `demo_07_structure/app/models/stock.py`：

```python
"""数据库模型"""
from sqlalchemy import Column, String, Float, Integer, DateTime
from sqlalchemy.sql import func
from app.database import Base

class Stock(Base):
    __tablename__ = "stocks"
    
    code = Column(String(6), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    price = Column(Float, default=0.0)
    change = Column(Float, default=0.0)
    volume = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

### 任务 5: Pydantic Schema

创建 `demo_07_structure/app/schemas/stock.py`：

```python
"""Pydantic 模型"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class StockBase(BaseModel):
    """股票基础模型"""
    code: str = Field(..., min_length=6, max_length=6)
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(0, ge=0)
    change: float = Field(0)
    volume: int = Field(0, ge=0)

class StockCreate(StockBase):
    """创建股票"""
    pass

class StockUpdate(BaseModel):
    """更新股票"""
    name: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    change: Optional[float] = None
    volume: Optional[int] = Field(None, ge=0)

class StockResponse(StockBase):
    """股票响应"""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}

class StockListResponse(BaseModel):
    """股票列表响应"""
    total: int
    items: List[StockResponse]
```

### 任务 6: 服务层

创建 `demo_07_structure/app/services/stock_service.py`：

```python
"""股票服务层"""
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.stock import Stock
from app.schemas.stock import StockCreate, StockUpdate

class StockService:
    """股票服务"""
    
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[Stock]:
        return db.query(Stock).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_by_code(db: Session, code: str) -> Optional[Stock]:
        return db.query(Stock).filter(Stock.code == code).first()
    
    @staticmethod
    def create(db: Session, stock_data: StockCreate) -> Stock:
        stock = Stock(**stock_data.model_dump())
        db.add(stock)
        db.commit()
        db.refresh(stock)
        return stock
    
    @staticmethod
    def update(db: Session, code: str, update_data: StockUpdate) -> Optional[Stock]:
        stock = db.query(Stock).filter(Stock.code == code).first()
        if not stock:
            return None
        
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(stock, key, value)
        
        db.commit()
        db.refresh(stock)
        return stock
    
    @staticmethod
    def delete(db: Session, code: str) -> bool:
        stock = db.query(Stock).filter(Stock.code == code).first()
        if not stock:
            return False
        
        db.delete(stock)
        db.commit()
        return True
    
    @staticmethod
    def count(db: Session) -> int:
        return db.query(Stock).count()
```

### 任务 7: API 路由

创建 `demo_07_structure/app/api/v1/stocks.py`：

```python
"""股票 API 路由"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.stock import (
    StockCreate, StockUpdate, StockResponse, StockListResponse
)
from app.services.stock_service import StockService

router = APIRouter(prefix="/stocks", tags=["股票"])

@router.get("", response_model=StockListResponse)
def list_stocks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取股票列表"""
    stocks = StockService.get_all(db, skip, limit)
    total = StockService.count(db)
    return StockListResponse(
        total=total,
        items=[StockResponse.model_validate(s) for s in stocks]
    )

@router.get("/{code}", response_model=StockResponse)
def get_stock(code: str, db: Session = Depends(get_db)):
    """获取单个股票"""
    stock = StockService.get_by_code(db, code)
    if not stock:
        raise HTTPException(status_code=404, detail=f"股票 {code} 不存在")
    return StockResponse.model_validate(stock)

@router.post("", response_model=StockResponse, status_code=201)
def create_stock(stock_data: StockCreate, db: Session = Depends(get_db)):
    """创建股票"""
    existing = StockService.get_by_code(db, stock_data.code)
    if existing:
        raise HTTPException(status_code=409, detail="股票已存在")
    return StockService.create(db, stock_data)

@router.put("/{code}", response_model=StockResponse)
def update_stock(
    code: str,
    update_data: StockUpdate,
    db: Session = Depends(get_db)
):
    """更新股票"""
    stock = StockService.update(db, code, update_data)
    if not stock:
        raise HTTPException(status_code=404, detail=f"股票 {code} 不存在")
    return StockResponse.model_validate(stock)

@router.delete("/{code}")
def delete_stock(code: str, db: Session = Depends(get_db)):
    """删除股票"""
    success = StockService.delete(db, code)
    if not success:
        raise HTTPException(status_code=404, detail=f"股票 {code} 不存在")
    return {"message": "删除成功"}
```

### 任务 8: API 入口

创建 `demo_07_structure/app/api/v1/__init__.py`：

```python
"""API v1 路由"""
from fastapi import APIRouter
from app.api.v1 import stocks

router = APIRouter(prefix="/api/v1")
router.include_router(stocks.router)

# 导出路由供主程序使用
__all__ = ["router"]
```

### 任务 9: 主程序

创建 `demo_07_structure/app/main.py`：

```python
"""FastAPI 应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.api.v1 import router as api_v1_router

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_v1_router)

@app.on_event("startup")
def startup_event():
    """启动事件"""
    init_db()
    print(f"{settings.APP_NAME} v{settings.APP_VERSION} 已启动")

@app.get("/")
def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

创建 `demo_07_structure/app/__init__.py`：

```python
"""应用包"""
```

## 测试

```bash
# 启动项目
cd demo_07_structure
uvicorn app.main:app --reload

# 测试 API
curl http://localhost:8000/api/v1/stocks
curl http://localhost:8000/api/v1/stocks/600519
```

## 下一步
阅读 `../docs/analysis/07_project_structure.md` 深入理解
