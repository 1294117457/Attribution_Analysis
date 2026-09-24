# 项目结构详解

## 一、为什么需要良好的项目结构？

### 小项目 vs 大项目

```python
# 小项目（100-500行）
main.py          # 全部代码
database.py      # 数据库
models.py        # 模型
routes.py        # 路由
# 可行，但代码量增长后难以维护

# 大项目（1000+行）
app/
├── api/         # API 路由
├── models/      # 数据库模型
├── schemas/     # Pydantic 模型
├── services/    # 业务逻辑
├── core/       # 核心功能
└── main.py     # 入口
# 职责分离，易于维护和测试
```

## 二、经典项目结构

### 结构1：功能型（推荐）

```
app/
├── __init__.py
├── main.py           # 应用入口
├── config.py         # 配置
├── database.py       # 数据库
│
├── api/              # API 层（路由）
│   ├── __init__.py
│   ├── deps.py       # 依赖（Depends）
│   └── v1/
│       ├── __init__.py
│       ├── stocks.py
│       ├── analysis.py
│       └── collector.py
│
├── models/           # 数据库模型
│   ├── __init__.py
│   ├── stock.py
│   ├── anomaly.py
│   └── user.py
│
├── schemas/          # Pydantic 模型（请求/响应）
│   ├── __init__.py
│   ├── stock.py
│   └── anomaly.py
│
├── services/         # 业务逻辑
│   ├── __init__.py
│   ├── stock_service.py
│   └── analyzer.py
│
├── core/             # 核心功能
│   ├── __init__.py
│   ├── security.py
│   ├── exceptions.py
│   └── logging.py
│
└── utils/            # 工具函数
    ├── __init__.py
    └── helpers.py
```

### 结构2：按领域划分

```
app/
├── main.py
├── config.py
│
├── stocks/           # 股票领域
│   ├── __init__.py
│   ├── routes.py     # API 路由
│   ├── models.py     # 数据库模型
│   ├── schemas.py    # Pydantic 模型
│   └── service.py    # 业务逻辑
│
├── analysis/          # 分析领域
│   ├── __init__.py
│   ├── routes.py
│   ├── models.py
│   └── service.py
│
└── core/             # 共享的核心功能
    ├── __init__.py
    └── config.py
```

## 三、各层职责

### 1. API 层（routes）

```python
# app/api/v1/stocks.py
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/stocks", tags=["股票"])

@router.get("")
def list_stocks():
    # 只处理：
    # - 参数验证（Query, Path）
    # - 调用 service
    # - 返回响应
    pass
```

### 2. Service 层（业务逻辑）

```python
# app/services/stock_service.py
class StockService:
    """股票业务逻辑"""
    
    def list_stocks(self, db, page, page_size):
        # 处理业务逻辑
        # 数据库查询
        # 数据处理
        # 返回结果
        pass
```

### 3. Model 层（数据库）

```python
# app/models/stock.py
class Stock(Base):
    __tablename__ = "stocks"
    code = Column(String, primary_key=True)
    # 只定义数据结构
```

### 4. Schema 层（数据验证）

```python
# app/schemas/stock.py
class StockCreate(BaseModel):
    code: str
    name: str
    # 定义 API 输入输出格式
```

## 四、分层的好处

```
分层隔离
┌─────────────────────────────────────┐
│         API Layer (路由)            │  变更：只影响 API
├─────────────────────────────────────┤
│         Service Layer (逻辑)         │  变更：只影响业务
├─────────────────────────────────────┤
│         Model Layer (数据库)         │  变更：只影响存储
└─────────────────────────────────────┘

测试隔离
├── API 测试   → Mock Service
├── Service 测试 → Mock Model
└── Model 测试  → 真实数据库
```

## 五、依赖注入设计

### 函数级依赖

```python
# app/api/deps.py
from app.database import get_db
from app.services.stock_service import StockService
from app.services.analyzer import AnalyzerService

def get_stock_service(db: Session = Depends(get_db)) -> StockService:
    return StockService(db)

def get_analyzer_service() -> AnalyzerService:
    return AnalyzerService()

# 使用
@router.get("/stocks")
def list_stocks(
    service: StockService = Depends(get_stock_service)
):
    return service.list()
```

### 类级依赖

```python
class StockController:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        self.service = StockService(db)
    
    @router.get("/stocks")
    def list_stocks(self):
        return self.service.list()
```

## 六、配置管理

### Pydantic Settings

```python
# app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "股票分析 API"
    DATABASE_URL: str = "sqlite:///./stocks.db"
    DEBUG: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

### .env 文件

```bash
# .env
APP_NAME=股票分析 API
DATABASE_URL=sqlite:///./stocks.db
DEBUG=true
```

## 七、数据库连接

### 单一数据库

```python
# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 多数据库（微服务）

```python
# 每个服务独立数据库
stocks_engine = create_engine(STOCKS_DB_URL)
analysis_engine = create_engine(ANALYSIS_DB_URL)

def get_stocks_db():
    db = sessionmaker(bind=stocks_engine)()
    try:
        yield db
    finally:
        db.close()
```

## 八、路由组织

### 路由注册

```python
# app/main.py
from app.api.v1 import router as api_v1

app = FastAPI()
app.include_router(api_v1)

# app/api/v1/__init__.py
from fastapi import APIRouter
from app.api.v1 import stocks, analysis

router = APIRouter(prefix="/api/v1")
router.include_router(stocks.router)
router.include_router(analysis.router)
```

### 路由前缀约定

```python
# 版本前缀
prefix="/api/v1"

# 功能前缀
prefix="/stocks"     # /api/v1/stocks
prefix="/analysis"  # /api/v1/analysis

# 标签（用于文档分组）
tags=["股票"]
tags=["分析"]
```

## 九、初始化代码

### startup 事件

```python
# app/main.py
@app.on_event("startup")
def startup_event():
    # 初始化数据库
    init_db()
    
    # 初始化缓存
    init_cache()
    
    # 加载配置
    load_config()
    
    print("应用启动完成")
```

### lifespan（FastAPI 0.89+）

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动
    init_db()
    yield
    # 关闭
    cleanup()

app = FastAPI(lifespan=lifespan)
```

## 十、实战：与你的项目结合

```
你的项目结构
├── app/
│   ├── main.py           # 已有
│   ├── api/
│   │   ├── collector.py  # 采集 API
│   │   ├── detector.py   # 检测 API
│   │   └── analysis.py   # 分析 API
│   ├── models/
│   │   ├── stock.py      # 股票模型
│   │   └── anomaly.py    # 异常模型
│   ├── schemas/
│   │   └── anomaly.py    # 异常 Pydantic 模型
│   └── services/
│       ├── collector.py   # 采集服务
│       ├── detector.py   # 检测服务
│       └── analyzer.py   # 分析服务
├── scripts/
│   └── data_manager.py   # 脚本
└── tests/
```

## 练习题

1. 重构你的项目，按上述结构组织代码
2. 创建 Service 层，把 API 路由中的业务逻辑抽离出来
3. 创建 Schema 层，定义所有 API 的请求/响应模型
4. 实现配置管理，支持环境变量和 .env 文件
5. 实现应用启动和关闭事件
