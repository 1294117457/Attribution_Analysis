# Python 后端开发指南（FastAPI + LangGraph）

> 面向 Java 开发者的 FastAPI 入门指南
> 适用对象：零 Python 经验，会 Java Spring Boot

---

## 目录

1. [环境准备](#1-环境准备)
2. [项目初始化](#2-项目初始化)
3. [架构总览](#3-架构总览)
4. [目录结构说明](#4-目录结构说明)
5. [核心概念速通](#5-核心概念速通)
6. [第一个 API：Hello World](#6-第一个-apihello-world)
7. [数据持久化：数据库配置](#7-数据持久化数据库配置)
8. [A股数据接入：AkShare](#8-a股数据接入akshare)
9. [定时任务：数据采集](#9-定时任务数据采集)
10. [下一步：LangGraph Agent](#10-下一步langgraph-agent)

---

## 1. 环境准备

### 1.1 安装 Python

```
Windows：
1. 官网下载 Python 3.11+：https://www.python.org/downloads/
2. 安装时勾选 ✅ Add Python to PATH
3. 打开 PowerShell，验证：
   python --version
   pip --version

Mac：
brew install python@3.11

验证：
python3 --version
```

### 1.2 安装 PyCharm（推荐 IDE）

```
下载地址：https://www.jetbrains.com/pycharm/download/
选择 Community（免费版）即可
```

### 1.3 创建虚拟环境（项目隔离）

```powershell
cd Attribution_Analysis/backend

# 创建虚拟环境（类似 Java 的 Maven/Gradle wrapper）
python -m venv venv

# 激活虚拟环境
# Windows：
.\venv\Scripts\activate

# Mac/Linux：
source venv/bin/activate

# 激活成功后，命令行会显示 (venv) 前缀
```

### 1.4 pip 换源（国内加速）

```powershell
# 临时换源（每次 pip install 前加）
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple 包名

# 永久换源
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 2. 项目初始化

### 2.1 创建项目（手动版）

```powershell
cd Attribution_Analysis/backend

# 确保在虚拟环境中
.\venv\Scripts\activate

# 安装核心依赖
pip install fastapi uvicorn sqlalchemy pymysql alembic akshare pandas

# 安装开发工具
pip install pytest black flake8

# 安装类型提示
pip install pydantic
```

### 2.2 初始化数据库（MySQL）

```sql
-- 创建数据库
CREATE DATABASE attribution_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户（可选）
CREATE USER 'attribution'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON attribution_db.* TO 'attribution'@'localhost';
FLUSH PRIVILEGES;
```

### 2.3 配置环境变量

在 `backend/` 目录下创建 `.env` 文件：

```env
# 数据库配置
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/attribution_db?charset=utf8mb4

# FastAPI 配置
APP_NAME=Attribution Analysis API
APP_VERSION=1.0.0
DEBUG=True

# AkShare 配置（免费，无需 API Key）
# 如需付费数据，可配置：
# TUSHARE_TOKEN=your_token_here

# LLM 配置（后续接入）
OPENAI_API_KEY=your_openai_key
DASHSCOPE_API_KEY=your_dashscope_key

# Redis 配置（可选）
REDIS_URL=redis://localhost:6379/0

# Qdrant 配置（可选，向量数据库）
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=experiences
```

### 2.4 安装依赖

```powershell
# 在 backend 目录下执行
pip install -r requirements.txt
```

---

## 3. 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI + LangGraph 后端                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  HTTP 层（路由 + 校验）                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  @app.post /api/analyze                                  │   │
│  │  @app.get  /api/klines                                   │   │
│  │  @app.get  /api/news                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                      │
│                            ▼                                      │
│  Service 层（业务逻辑）                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  KLineService    NewsService    AnalyzeService          │   │
│  │  DataCollector   ReportService                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                      │
│                            ▼                                      │
│  LangGraph 层（AI 编排）                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  归因Agent   异常检测Agent   报告生成Agent               │   │
│  │  Tool: query_klines    Tool: query_news                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                      │
│                            ▼                                      │
│  数据层（持久化）                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  MySQL（klines, news, reports）                        │   │
│  │  Qdrant（经验向量）                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. 目录结构说明

```
backend/
├── app/                          # 主应用包
│   ├── __init__.py               # 包标记（Python 要求）
│   │
│   ├── main.py                   # 入口文件（类似 SpringBootApplication）
│   │                             # 启动 uvicorn、注册路由、配置中间件
│   │
│   ├── config.py                 # 配置管理（类似 application.yml）
│   │                             # 从 .env 读取配置，提供全局配置对象
│   │
│   ├── api/                      # API 路由层（类似 Controller）
│   │   ├── __init__.py
│   │   ├── v1/                   # API v1 版本
│   │   │   ├── __init__.py
│   │   │   ├── router.py         # 路由聚合（类似 @RequestMapping）
│   │   │   ├── klines.py         # K 线相关接口
│   │   │   ├── news.py           # 新闻相关接口
│   │   │   └── analyze.py        # 分析接口
│   │   └── deps.py               # 依赖注入（类似 Depends）
│   │
│   ├── models/                   # 数据库模型（类似 JPA Entity）
│   │   ├── __init__.py
│   │   ├── base.py               # SQLAlchemy 基类
│   │   ├── kline.py              # K 线表
│   │   ├── news.py               # 新闻表
│   │   └── report.py             # 报告表
│   │
│   ├── schemas/                  # Pydantic 模型（类似 DTO）
│   │   ├── __init__.py
│   │   ├── kline.py              # K 线请求/响应模型
│   │   ├── news.py               # 新闻请求/响应模型
│   │   └── analyze.py            # 分析请求/响应模型
│   │
│   ├── services/                 # 业务逻辑层（类似 @Service）
│   │   ├── __init__.py
│   │   ├── kline_service.py      # K 线业务逻辑
│   │   ├── news_service.py       # 新闻业务逻辑
│   │   ├── collector_service.py  # 数据采集（AkShare）
│   │   └── analyze_service.py    # 分析业务逻辑
│   │
│   ├── db/                       # 数据库连接层
│   │   ├── __init__.py
│   │   ├── database.py           # 数据库连接
│   │   └── repositories/         # 数据仓库（类似 JPA Repository）
│   │       ├── __init__.py
│   │       ├── kline_repo.py
│   │       └── news_repo.py
│   │
│   ├── agents/                   # LangGraph Agent 层
│   │   ├── __init__.py
│   │   ├── state.py             # Agent 状态定义
│   │   ├── tools/               # Agent 工具
│   │   │   ├── __init__.py
│   │   │   ├── query_tools.py   # 数据查询工具
│   │   │   └── analysis_tools.py # 分析工具
│   │   ├── nodes/               # Agent 节点
│   │   │   ├── __init__.py
│   │   │   ├── anomaly_node.py  # 异常检测节点
│   │   │   ├── attribution_node.py # 归因分析节点
│   │   │   └── report_node.py   # 报告生成节点
│   │   └── graphs/              # 工作流图
│   │       ├── __init__.py
│   │       ├── attribution_graph.py # 归因分析工作流
│   │       └── anomaly_graph.py # 异常检测工作流
│   │
│   └── tasks/                   # 定时任务
│       ├── __init__.py
│       └── scheduler.py         # APScheduler 配置
│
├── tests/                       # 测试
│   ├── __init__.py
│   ├── test_klines.py
│   └── test_analyze.py
│
├── scripts/                     # 脚本
│   ├── init_db.py              # 数据库初始化
│   └── collect_data.py         # 数据采集脚本
│
├── .env                         # 环境变量（不提交 git）
├── .env.example                 # 环境变量示例
├── requirements.txt             # 依赖列表
├── pyproject.toml              # 项目配置（PEP 621）
├── alembic.ini                 # Alembic 数据库迁移配置
├── alembic/                    # Alembic 迁移脚本
│   ├── env.py
│   └── versions/
│
└── README.md                   # 后端 README
```

### 目录对应 Java 概念对照

```
Python FastAPI                 Java Spring Boot
─────────────────────────────────────────────────────
app/main.py                   Application.java（启动类）
app/config.py                @Configuration + @Value
app/api/v1/klines.py         @RestController + @GetMapping
app/schemas/kline.py          @RequestBody DTO + @Valid
app/models/kline.py           @Entity + JPA Entity
app/services/kline_service.py @Service
app/db/repositories/         @Repository + JPA Repository
app/agents/                   @Component + 业务逻辑
app/tasks/scheduler.py        @Scheduled
```

---

## 5. 核心概念速通

### 5.1 Python 基础（Java 对比）

```python
# ============ 1. 导入 ============
# Python：import
# Java：import

from fastapi import FastAPI              # 从 fastapi 包导入 FastAPI
from pydantic import BaseModel, Field   # 从 pydantic 导入
from typing import Optional, List       # 类型提示（类似 Java Generics）
from datetime import date, datetime     # 日期时间
from enum import Enum                   # 枚举

# ============ 2. 类型提示 ============
# Python 用 -> 指定返回值类型，参数用 : 指定类型
def get_user(user_id: int) -> str:
    return f"User {user_id}"

# Optional[X] = X 或 None（类似 @Nullable）
name: Optional[str] = None

# List[str] = List<String>
symbols: List[str] = ["600519", "000001"]

# ============ 3. 数据类 ============
# Python 的 Pydantic BaseModel 类似 Java Bean
class User(BaseModel):
    id: int
    name: str
    email: Optional[str] = None  # 有默认值，可选

# ============ 4. 异步 ============
# Python 的 async/await 类似 Java CompletableFuture
async def get_data():
    result = await fetch_from_db()  # 异步等待
    return result

# ============ 5. 类和继承 ============
class Animal:
    def __init__(self, name: str):   # __init__ = 构造方法
        self.name = name
    
    def speak(self) -> str:
        return "..."

class Dog(Animal):
    def __init__(self, name: str, breed: str):
        super().__init__(name)       # super() = super
        self.breed = breed
    
    def speak(self) -> str:
        return "汪汪"

# ============ 6. 注解装饰器 ============
# Python @decorator 类似 Java 注解
# FastAPI 的 @app.get() 就是装饰器

def my_decorator(func):
    def wrapper(*args, **kwargs):
        print("Before")
        result = func(*args, **kwargs)
        print("After")
        return result
    return wrapper

@my_decorator
def hello():
    print("Hello")

# ============ 7. 字典和 JSON ============
# Python dict 类似 Java Map
user = {"name": "张三", "age": 30}
print(user["name"])        # 张三
print(user.get("email"))   # None（不存在）

# ============ 8. 列表操作 ============
numbers = [1, 2, 3, 4, 5]

# 列表推导式（类似 Java Stream）
squares = [x**2 for x in numbers]     # [1, 4, 9, 16, 25]
evens = [x for x in numbers if x % 2 == 0]  # [2, 4]

# ============ 9. None vs null ============
# Python 的 None 类似 Java 的 null
name = None

# ============ 10. 字符串格式化 ============
# f-string（类似 String.format）
name = "张三"
age = 30
print(f"{name} is {age} years old")  # 张三 is 30 years old

# ============ 11. 异常处理 ============
try:
    result = 10 / 0
except ZeroDivisionError as e:
    print(f"Error: {e}")
finally:
    print("Always runs")

# ============ 12. with 语句 ============
# 类似 Java try-with-resources
with open("file.txt", "r") as f:
    content = f.read()
# 文件自动关闭
```

### 5.2 FastAPI 核心概念

```python
# ==================== 1. 创建应用 ====================
app = FastAPI(
    title="归因分析 API",
    version="1.0.0",
    description="智能金融数据归因分析平台后端"
)

# ==================== 2. 路径参数（类似 @PathVariable）====================
@app.get("/api/klines/{symbol}")
async def get_kline(symbol: str):  # symbol 就是路径参数
    return {"symbol": symbol}

# 访问：GET /api/klines/600519

# ==================== 3. Query 参数（类似 @RequestParam）====================
@app.get("/api/klines")
async def get_klines(
    symbol: str,              # 必需参数
    start_date: str,         # 必需参数
    end_date: str = "today"  # 可选参数，有默认值
):
    return {"symbol": symbol, "start": start_date, "end": end_date}

# 访问：GET /api/klines?symbol=600519&start_date=2026-01-01

# ==================== 4. 请求体（类似 @RequestBody）====================
class KLineQuery(BaseModel):
    symbol: str
    start_date: date
    end_date: date

@app.post("/api/klines")
async def query_klines(query: KLineQuery):  # 自动解析 JSON 请求体
    return {"data": query}

# 请求：
# {
#   "symbol": "600519",
#   "start_date": "2026-01-01",
#   "end_date": "2026-06-25"
# }

# ==================== 5. Pydantic 校验（类似 @Valid + @NotNull）====================
class User(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)  # 不能为空，长度 1-100
    age: int = Field(..., ge=0, le=150)                   # 0-150 之间
    email: Optional[str] = None
    
    class Config:
        json_schema_extra = {  # OpenAPI 文档示例
            "example": {
                "name": "张三",
                "age": 30,
                "email": "zhangsan@example.com"
            }
        }

# ==================== 6. 响应模型 ====================
class KLineResponse(BaseModel):
    code: str
    name: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float

@app.get("/api/klines/{symbol}", response_model=KLineResponse)
async def get_kline(symbol: str):
    # 返回会自动转换为响应模型格式
    return {"code": symbol, "name": "贵州茅台", ...}

# ==================== 7. 依赖注入（类似 @Autowired）====================
# 定义依赖
async def get_db():
    db = SessionLocal()
    try:
        yield db  # 类似 @PreDestroy
    finally:
        db.close()

# 使用依赖
@app.get("/api/klines")
async def get_klines(db: Session = Depends(get_db)):  # 自动注入
    result = db.query(KLine).all()
    return result

# ==================== 8. 状态码和错误 ====================
from fastapi import HTTPException, status

@app.get("/api/klines/{symbol}")
async def get_kline(symbol: str):
    kline = db.query(KLine).filter(KLine.code == symbol).first()
    if not kline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"股票 {symbol} 不存在"
        )
    return kline

# ==================== 9. 异步（重要！） ====================
# FastAPI 默认异步，需要用 async def
@app.get("/api/klines")
async def get_klines():  # 异步函数
    # 正确：用 await
    data = await fetch_from_api()
    
    # 如果是同步库，用 run_in_executor 包装
    from concurrent.futures import ThreadPoolExecutor
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, sync_function)
    
    return data

# ==================== 10. 中间件（类似 Filter）====================
from fastapi import Request

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

### 5.3 SQLAlchemy 核心概念

```python
# ==================== 1. 创建引擎（类似 DataSource）====================
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "mysql+pymysql://root:password@localhost:3306/attribution_db"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # 连接前测试
    pool_size=10,            # 连接池大小
    max_overflow=20          # 最大溢出
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ==================== 2. 定义模型（类似 JPA Entity）====================
from sqlalchemy import Column, Integer, String, Float, Date, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()  # 基类

class KLine(Base):
    __tablename__ = "klines"  # 表名
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), index=True, nullable=False)      # 股票代码
    name = Column(String(50), nullable=False)                    # 股票名称
    date = Column(Date, index=True, nullable=False)              # 日期
    open = Column(Float, nullable=False)                         # 开盘价
    high = Column(Float, nullable=False)                         # 最高价
    low = Column(Float, nullable=False)                         # 最低价
    close = Column(Float, nullable=False)                        # 收盘价
    volume = Column(Float, nullable=False)                       # 成交量
    amount = Column(Float, nullable=False)                       # 成交额
    
    # 索引
    __table_args__ = (
        Index('idx_code_date', 'code', 'date'),  # 联合索引
    )

# ==================== 3. CRUD 操作 ====================
# 获取连接
db = SessionLocal()

# 创建
new_kline = KLine(code="600519", name="贵州茅台", date=today, ...)
db.add(new_kline)
db.commit()

# 查询
kline = db.query(KLine).filter(KLine.code == "600519").first()
klines = db.query(KLine).filter(
    KLine.code == "600519",
    KLine.date >= start_date,
    KLine.date <= end_date
).order_by(KLine.date).all()

# 更新
kline.close = 1800.0
db.commit()

# 删除
db.delete(kline)
db.commit()

# 关闭
db.close()

# ==================== 4. Repository 模式（推荐）====================
class KLineRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_code(self, code: str) -> Optional[KLine]:
        return self.db.query(KLine).filter(KLine.code == code).first()
    
    def get_by_code_and_date_range(
        self, code: str, start: date, end: date
    ) -> List[KLine]:
        return self.db.query(KLine).filter(
            KLine.code == code,
            KLine.date >= start,
            KLine.date <= end
        ).order_by(KLine.date).all()
    
    def create(self, kline: KLine) -> KLine:
        self.db.add(kline)
        self.db.commit()
        self.db.refresh(kline)
        return kline
    
    def bulk_create(self, klines: List[KLine]) -> List[KLine]:
        self.db.bulk_save_objects(klines)
        self.db.commit()
        return klines
```

---

## 6. 第一个 API：Hello World

### 6.1 创建项目

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── router.py
│   └── models/
│       ├── __init__.py
│       └── base.py
├── requirements.txt
└── .env
```

### 6.2 入口文件 main.py

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1 import router as api_v1

# 创建应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="智能金融数据归因分析平台后端 API",
    docs_url="/docs",      # Swagger UI 文档
    redoc_url="/redoc",    # ReDoc 文档
    openapi_url="/openapi.json"  # OpenAPI JSON
)

# CORS 配置（允许前端跨域）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # 前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(
    api_v1.router,
    prefix="/api/v1",
    tags=["v1"]
)

# 健康检查
@app.get("/health", tags=["健康检查"])
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}

# 启动提示
@app.on_event("startup")
async def startup_event():
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动中...")
    print(f"📚 API 文档: http://localhost:8000/docs")

@app.on_event("shutdown")
async def shutdown_event():
    print(f"👋 {settings.APP_NAME} 已关闭")
```

### 6.3 配置 config.py

```python
import os
from pathlib import Path
from pydantic_settings import BaseSettings

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用
    APP_NAME: str = "Attribution Analysis API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 数据库
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/attribution_db?charset=utf8mb4"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Qdrant 向量数据库
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "experiences"
    
    # LLM API Keys
    OPENAI_API_KEY: str = ""
    DASHSCOPE_API_KEY: str = ""
    
    class Config:
        env_file = BASE_DIR / ".env"
        case_sensitive = True


settings = Settings()
```

### 6.4 路由 router.py

```python
from fastapi import APIRouter

router = APIRouter()

# 导入子路由
from app.api.v1 import klines, news, analyze

# 注册子路由
router.include_router(klines.router, prefix="/klines", tags=["K线数据"])
router.include_router(news.router, prefix="/news", tags=["新闻数据"])
router.include_router(analyze.router, prefix="/analyze", tags=["分析服务"])
```

### 6.5 K线接口 klines.py

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import date, datetime

from app.schemas.kline import KLineResponse, KLineQueryRequest
from app.services.kline_service import KLineService
from app.db.session import get_db

router = APIRouter()


@router.get("/symbols", summary="获取股票列表")
async def get_symbols(
    market: str = Query("A股", description="市场"),
    db=Depends(get_db)
):
    """获取支持的所有股票代码"""
    service = KLineService(db)
    return await service.get_symbols(market)


@router.get("/{symbol}", response_model=KLineResponse, summary="获取单条K线")
async def get_kline(
    symbol: str,
    trade_date: date = Query(..., description="交易日期"),
    db=Depends(get_db)
):
    """获取指定股票指定日期的K线数据"""
    service = KLineService(db)
    kline = await service.get_kline(symbol, trade_date)
    if not kline:
        raise HTTPException(status_code=404, detail=f"股票 {symbol} 在 {trade_date} 无数据")
    return kline


@router.get("", response_model=List[KLineResponse], summary="获取K线历史")
async def get_klines(
    symbol: str = Query(..., description="股票代码"),
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    db=Depends(get_db)
):
    """获取指定股票日期范围的K线数据"""
    service = KLineService(db)
    return await service.get_klines(symbol, start_date, end_date)


@router.post("/query", response_model=List[KLineResponse], summary="查询K线")
async def query_klines(
    request: KLineQueryRequest,
    db=Depends(get_db)
):
    """通过请求体查询K线数据"""
    service = KLineService(db)
    return await service.get_klines(
        request.symbol,
        request.start_date,
        request.end_date
    )
```

### 6.6 Schema（DTO）

```python
# app/schemas/kline.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime


class KLineResponse(BaseModel):
    """K线响应模型"""
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    date: date = Field(..., description="交易日期")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: float = Field(..., description="成交量")
    amount: float = Field(..., description="成交额")
    change: float = Field(None, description="涨跌幅(%)")
    turnover: float = Field(None, description="换手率(%)")
    
    class Config:
        from_attributes = True


class KLineQueryRequest(BaseModel):
    """K线查询请求"""
    symbol: str = Field(..., min_length=6, max_length=6, description="股票代码，6位数字")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "600519",
                "start_date": "2026-01-01",
                "end_date": "2026-06-25"
            }
        }


class StockInfo(BaseModel):
    """股票基本信息"""
    code: str
    name: str
    industry: Optional[str] = None
    market: Optional[str] = None
```

### 6.7 Service

```python
# app/services/kline_service.py
from typing import List, Optional
from datetime import date

from app.models.kline import KLine
from app.schemas.kline import KLineResponse, StockInfo
from app.db.repositories.kline_repo import KLineRepository


class KLineService:
    """K线服务"""
    
    def __init__(self, db):
        self.repo = KLineRepository(db)
    
    async def get_symbols(self, market: str = "A股") -> List[StockInfo]:
        """获取股票列表"""
        # 这里后续接入 AkShare 获取真实数据
        return []
    
    async def get_kline(self, symbol: str, trade_date: date) -> Optional[KLineResponse]:
        """获取单条K线"""
        kline = self.repo.get_by_code_and_date(symbol, trade_date)
        if kline:
            return self._to_response(kline)
        return None
    
    async def get_klines(
        self, symbol: str, start_date: date, end_date: date
    ) -> List[KLineResponse]:
        """获取K线历史"""
        klines = self.repo.get_by_date_range(symbol, start_date, end_date)
        return [self._to_response(k) for k in klines]
    
    def _to_response(self, kline: KLine) -> KLineResponse:
        """转换为响应模型"""
        return KLineResponse(
            code=kline.code,
            name=kline.name,
            date=kline.date,
            open=kline.open,
            high=kline.high,
            low=kline.low,
            close=kline.close,
            volume=kline.volume,
            amount=kline.amount,
            change=kline.close / kline.open * 100 - 100 if kline.open else None,
        )
```

### 6.8 启动服务

```powershell
cd backend

# 激活虚拟环境
.\venv\Scripts\activate

# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 输出：
# Uvicorn running on http://127.0.0.1:8000
# API 文档：http://127.0.0.1:8000/docs
```

---

## 7. 数据持久化：数据库配置

### 7.1 安装依赖

```powershell
pip install sqlalchemy pymysql cryptography pydantic-settings
```

### 7.2 数据库连接（PostgreSQL）

```python
# app/db/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# 同步引擎（用于迁移和脚本）
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,
)

# 异步引擎（用于 FastAPI 异步操作）
async_engine = create_async_engine(
    settings.DATABASE_URL_ASYNC,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# 异步会话工厂
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# 创建基类
Base = declarative_base()


# app/db/session.py
from app.db.database import engine, AsyncSessionLocal

def get_db():
    """获取数据库会话的依赖（同步）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_db_async():
    """获取数据库会话的依赖（异步）"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

### 7.3 定义模型

```python
# app/models/kline.py
from sqlalchemy import Column, Integer, String, Float, Date, Index
from app.db.database import Base


class KLine(Base):
    """K线表"""
    __tablename__ = "klines"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, index=True, comment="股票代码")
    name = Column(String(50), nullable=False, comment="股票名称")
    date = Column(Date, nullable=False, index=True, comment="交易日期")
    open = Column(Float, nullable=False, comment="开盘价")
    high = Column(Float, nullable=False, comment="最高价")
    low = Column(Float, nullable=False, comment="最低价")
    close = Column(Float, nullable=False, comment="收盘价")
    volume = Column(Float, nullable=False, comment="成交量(手)")
    amount = Column(Float, nullable=False, comment="成交额(元)")
    change_pct = Column(Float, nullable=True, comment="涨跌幅(%)")
    turnover_rate = Column(Float, nullable=True, comment="换手率(%)")
    
    __table_args__ = (
        Index('idx_code_date', 'code', 'date', unique=True),
    )
```

### 7.4 Alembic 数据库迁移

```powershell
# 安装 Alembic
pip install alembic

# 初始化 Alembic
alembic init alembic

# 配置 alembic.ini（修改 sqlalchemy.url）
# sqlalchemy.url = mysql+pymysql://root:password@localhost:3306/attribution_db

# 修改 alembic/env.py（添加 model 导入）
from app.models.base import Base
target_metadata = Base.metadata

# 创建迁移
alembic revision --autogenerate -m "create klines table"

# 执行迁移
alembic upgrade head
```

### 7.5 Repository

```python
# app/db/repositories/kline_repo.py
from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session

from app.models.kline import KLine


class KLineRepository:
    """K线数据仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_code_and_date(
        self, code: str, trade_date: date
    ) -> Optional[KLine]:
        """根据代码和日期获取K线"""
        return self.db.query(KLine).filter(
            KLine.code == code,
            KLine.date == trade_date
        ).first()
    
    def get_by_date_range(
        self, code: str, start: date, end: date
    ) -> List[KLine]:
        """根据日期范围获取K线"""
        return self.db.query(KLine).filter(
            KLine.code == code,
            KLine.date >= start,
            KLine.date <= end
        ).order_by(KLine.date).all()
    
    def get_latest(self, code: str, limit: int = 100) -> List[KLine]:
        """获取最近N条K线"""
        return self.db.query(KLine).filter(
            KLine.code == code
        ).order_by(KLine.date.desc()).limit(limit).all()
    
    def bulk_insert(self, klines: List[KLine]) -> int:
        """批量插入K线"""
        self.db.bulk_save_objects(klines)
        self.db.commit()
        return len(klines)
    
    def count(self, code: Optional[str] = None) -> int:
        """统计K线数量"""
        query = self.db.query(KLine)
        if code:
            query = query.filter(KLine.code == code)
        return query.count()
```

---

## 8. A股数据接入：AkShare

### 8.1 AkShare 简介

```
AkShare = 免费、开源、Python 写的金融数据接口库

功能：
• A股实时行情、历史K线
• 股票列表、财务数据
• 基金、期货、期权
• 宏观经济数据
• 新闻资讯

官网：https://akshare.akfamily.xyz/
```

### 8.2 安装 AkShare

```powershell
pip install akshare pandas numpy
```

### 8.3 AkShare 快速使用

```python
import akshare as ak

# ==================== 1. 获取A股实时行情 ====================
df = ak.stock_zh_a_spot_em()
print(df[['代码', '名称', '最新价', '涨跌幅', '成交量', '成交额']])

# ==================== 2. 获取K线历史数据 ====================
# 日K线
df = ak.stock_zh_a_hist(
    symbol="600519",      # 股票代码
    period="daily",       # 日线
    start_date="20260101",  # 开始日期
    end_date="20260625",     # 结束日期
    adjust="qfq"          # 前复权
)
print(df)

# ==================== 3. 获取股票列表 ====================
# 上证A股
df = ak.stock_info_a_code_name()
print(df.head(20))

# ==================== 4. 获取实时分时数据 ====================
df = ak.stock_zh_a_spot_em()
print(df[['代码', '名称', '实时价格']])

# ==================== 5. 获取新闻资讯 ====================
df = ak.stock_news_em(symbol="600519")
print(df[['发布时间', '新闻标题', '新闻内容']])

# ==================== 6. 获取公告 ====================
df = ak.stock_report_disclosure_sina(stock="600519")
print(df)
```

### 8.4 AkShare 数据格式

```python
# stock_zh_a_hist 返回的 DataFrame 结构：
"""
     日期       股票代码    名称     开盘    收盘    最高    最低     成交量           成交额   振幅  涨跌幅  涨跌额  换手率
0  2026-06-25  600519   贵州茅台  1450.0  1468.0  1475.0  1445.0  35210.00  51234567890.0  2.07  1.24  18.0  0.29
1  2026-06-24  600519   贵州茅台  1440.0  1450.0  1460.0  1435.0  28000.00  40234567890.0  1.74 -0.69 -10.0  0.23
"""

# 转换为数据库格式：
kline = KLine(
    code=row['股票代码'],       # "600519"
    name=row['名称'],           # "贵州茅台"
    date=pd.to_datetime(row['日期']).date(),  # date 对象
    open=float(row['开盘']),    # 开盘价
    high=float(row['最高']),    # 最高价
    low=float(row['最低']),     # 最低价
    close=float(row['收盘']),   # 收盘价
    volume=float(row['成交量']),  # 成交量
    amount=float(row['成交额']),  # 成交额
    change_pct=float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else None,
    turnover_rate=float(row['换手率']) if pd.notna(row['换手率']) else None,
)
```

### 8.5 数据采集服务

```python
# app/services/collector_service.py
import akshare as ak
import pandas as pd
from typing import List, Optional
from datetime import date, datetime, timedelta
import asyncio
from sqlalchemy.orm import Session

from app.models.kline import KLine
from app.db.repositories.kline_repo import KLineRepository
from app.config import settings


class CollectorService:
    """数据采集服务（AkShare）"""
    
    def __init__(self, db: Session):
        self.db = db
        self.repo = KLineRepository(db)
    
    # ==================== 采集单只股票K线 ====================
    async def collect_klines(
        self, 
        symbol: str, 
        start_date: date, 
        end_date: date,
        adjust: str = "qfq"  # qfq=前复权, hfq=后复权, None=不复权
    ) -> int:
        """
        采集指定股票指定日期范围的K线数据
        
        Args:
            symbol: 股票代码，如 "600519"
            start_date: 开始日期
            end_date: 结束日期
            adjust: 复权类型
            
        Returns:
            采集的数据条数
        """
        try:
            # 调用 AkShare（同步，需要在线程池中运行）
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None,
                lambda: ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d"),
                    adjust=adjust
                )
            )
            
            # 转换为 KLine 模型列表
            klines = self._convert_to_klines(df)
            
            if klines:
                # 批量插入
                self.repo.bulk_insert(klines)
                print(f"✅ 采集 {symbol} K线 {len(klines)} 条")
            else:
                print(f"⚠️ {symbol} 无数据")
            
            return len(klines)
            
        except Exception as e:
            print(f"❌ 采集 {symbol} 失败: {e}")
            return 0
    
    # ==================== 采集多只股票K线 ====================
    async def collect_klines_batch(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date,
        delay: float = 1.0  # 请求间隔（秒），避免频率限制
    ) -> dict:
        """
        批量采集多只股票K线
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            delay: 请求间隔
            
        Returns:
            采集结果统计
        """
        results = {"success": 0, "failed": 0, "total": 0}
        
        for symbol in symbols:
            count = await self.collect_klines(symbol, start_date, end_date)
            if count > 0:
                results["success"] += 1
            else:
                results["failed"] += 1
            results["total"] += count
            
            # 避免频率限制
            if delay > 0:
                await asyncio.sleep(delay)
        
        return results
    
    # ==================== 采集全市场K线 ====================
    async def collect_market_klines(
        self,
        market: str = "all",
        start_date: Optional[date] = None,
        days: int = 30  # 默认采集最近30天
    ) -> dict:
        """
        采集全市场或指定市场的K线
        
        Args:
            market: 市场类型，all=全部, sh=上海, sz=深圳
            start_date: 开始日期（默认30天前）
            days: 采集天数
            
        Returns:
            采集结果统计
        """
        if start_date is None:
            start_date = date.today() - timedelta(days=days)
        end_date = date.today()
        
        # 获取股票列表
        symbols = await self.get_stock_list(market)
        print(f"📊 获取到 {len(symbols)} 只股票")
        
        # 批量采集（带并发控制）
        results = {"success": 0, "failed": 0, "total": 0}
        
        # 并发数控制
        semaphore = asyncio.Semaphore(5)  # 最多5个并发
        
        async def collect_with_limit(symbol: str):
            async with semaphore:
                return await self.collect_klines(symbol, start_date, end_date)
        
        tasks = [collect_with_limit(s) for s in symbols]
        
        for i, coro in enumerate(asyncio.as_completed(tasks), 1):
            count = await coro
            if count > 0:
                results["success"] += 1
            else:
                results["failed"] += 1
            results["total"] += count
            
            # 每100只打印进度
            if i % 100 == 0:
                print(f"📈 进度: {i}/{len(symbols)}, 成功: {results['success']}, 失败: {results['failed']}")
        
        return results
    
    # ==================== 获取股票列表 ====================
    async def get_stock_list(self, market: str = "A股") -> List[str]:
        """
        获取股票代码列表
        
        Args:
            market: 市场类型
            
        Returns:
            股票代码列表
        """
        try:
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None,
                lambda: ak.stock_info_a_code_name()
            )
            return df['code'].tolist()
        except Exception as e:
            print(f"❌ 获取股票列表失败: {e}")
            return []
    
    # ==================== 采集新闻 ====================
    async def collect_news(self, symbol: str, days: int = 7) -> int:
        """
        采集指定股票的新闻
        
        Args:
            symbol: 股票代码
            days: 最近几天
            
        Returns:
            采集的新闻条数
        """
        try:
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None,
                lambda: ak.stock_news_em(symbol=symbol)
            )
            
            # 处理数据...
            print(f"✅ 采集 {symbol} 新闻 {len(df)} 条")
            return len(df)
            
        except Exception as e:
            print(f"❌ 采集 {symbol} 新闻失败: {e}")
            return 0
    
    # ==================== 辅助方法 ====================
    def _convert_to_klines(self, df: pd.DataFrame) -> List[KLine]:
        """将 DataFrame 转换为 KLine 模型列表"""
        klines = []
        
        for _, row in df.iterrows():
            try:
                kline = KLine(
                    code=str(row['股票代码']),
                    name=str(row['名称']),
                    date=pd.to_datetime(row['日期']).date(),
                    open=float(row['开盘']),
                    high=float(row['最高']),
                    low=float(row['最低']),
                    close=float(row['收盘']),
                    volume=float(row['成交量']),
                    amount=float(row['成交额']),
                    change_pct=float(row['涨跌幅']) if pd.notna(row.get('涨跌幅')) else None,
                    turnover_rate=float(row['换手率']) if pd.notna(row.get('换手率')) else None,
                )
                klines.append(kline)
            except Exception as e:
                print(f"⚠️ 数据转换错误: {e}, row={row.to_dict()}")
                continue
        
        return klines
```

### 8.6 接入 API

```python
# app/api/v1/klines.py 新增采集接口

from fastapi import APIRouter, Depends, BackgroundTasks
from datetime import date, timedelta
from app.db.session import get_db

router = APIRouter()


@router.post("/collect", summary="采集K线数据")
async def collect_klines(
    symbol: str,
    start_date: date,
    end_date: date,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """
    采集指定股票的K线数据（后台执行）
    
    - symbol: 股票代码，如 "600519"
    - start_date: 开始日期
    - end_date: 结束日期
    """
    service = CollectorService(db)
    
    # 后台执行采集
    background_tasks.add_task(
        service.collect_klines, symbol, start_date, end_date
    )
    
    return {
        "message": f"开始采集 {symbol} K线数据",
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "status": "pending"
    }


@router.post("/collect/batch", summary="批量采集K线数据")
async def collect_klines_batch(
    symbols: List[str],
    start_date: date,
    end_date: date,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """
    批量采集多只股票的K线数据（后台执行）
    
    - symbols: 股票代码列表
    - start_date: 开始日期
    - end_date: 结束日期
    """
    service = CollectorService(db)
    
    # 后台执行
    background_tasks.add_task(
        service.collect_klines_batch, symbols, start_date, end_date
    )
    
    return {
        "message": f"开始批量采集 {len(symbols)} 只股票 K线数据",
        "symbols": symbols,
        "count": len(symbols),
        "status": "pending"
    }


@router.post("/collect/market", summary="采集全市场K线数据")
async def collect_market_klines(
    days: int = Query(30, ge=1, le=365, description="采集天数"),
    market: str = Query("all", description="市场类型"),
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """
    采集全市场K线数据（后台执行）
    
    - days: 采集最近多少天
    - market: 市场类型，all=全部, sh=上海, sz=深圳
    """
    service = CollectorService(db)
    
    # 后台执行
    background_tasks.add_task(
        service.collect_market_klines, market, None, days
    )
    
    return {
        "message": f"开始采集全市场K线数据（最近 {days} 天）",
        "days": days,
        "status": "pending"
    }
```

---

## 9. 定时任务：数据采集

### 9.1 安装 APScheduler

```powershell
pip install apscheduler
```

### 9.2 定时任务配置

```python
# app/tasks/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, time
import pytz

from app.services.collector_service import CollectorService
from app.db.session import SessionLocal


# 创建调度器（使用异步版本）
scheduler = AsyncIOScheduler(timezone=pytz.timezone("Asia/Shanghai"))


def collect_daily_klines():
    """每日收盘后采集K线（下午16:00执行）"""
    db = SessionLocal()
    try:
        service = CollectorService(db)
        # 采集当天数据
        from datetime import date, timedelta
        today = date.today()
        start = today - timedelta(days=365)  # 采集一年数据
        
        # 采集全市场
        import asyncio
        asyncio.run(service.collect_market_klines(
            market="all",
            start_date=start,
            days=1
        ))
    finally:
        db.close()


def collect_realtime_data():
    """每5分钟采集实时行情"""
    db = SessionLocal()
    try:
        service = CollectorService(db)
        from datetime import date
        today = date.today()
        
        # 只采集重点关注的股票
        symbols = ["600519", "000858", "601318"]  # 白酒、保险龙头
        import asyncio
        asyncio.run(service.collect_klines_batch(
            symbols=symbols,
            start_date=today,
            end_date=today,
            delay=0.5
        ))
    finally:
        db.close()


def setup_scheduler():
    """配置定时任务"""
    
    # 每日16:00（收盘后）采集日K线
    scheduler.add_job(
        func=collect_daily_klines,
        trigger=CronTrigger(hour=16, minute=0, timezone="Asia/Shanghai"),
        id="collect_daily_klines",
        name="每日K线采集",
        replace_existing=True,
    )
    
    # 每5分钟采集实时数据
    scheduler.add_job(
        func=collect_realtime_data,
        trigger=IntervalTrigger(minutes=5),
        id="collect_realtime",
        name="实时行情采集",
        replace_existing=True,
    )
    
    print("⏰ 定时任务已配置")


def start_scheduler():
    """启动调度器"""
    setup_scheduler()
    scheduler.start()
    print("🚀 调度器已启动")


def stop_scheduler():
    """停止调度器"""
    scheduler.shutdown()
    print("👋 调度器已停止")
```

### 9.3 在 main.py 中集成

```python
# app/main.py

# 在文件顶部导入
from app.tasks.scheduler import start_scheduler, stop_scheduler

# 在应用创建后启动调度器
app = FastAPI(...)

@app.on_event("startup")
async def startup_event():
    # 原有启动逻辑...
    start_scheduler()  # 启动定时任务

@app.on_event("shutdown")
async def shutdown_event():
    stop_scheduler()  # 停止定时任务
    # 原有关闭逻辑...
```

---

## 10. 下一步：LangGraph Agent

### 10.1 LangGraph 简介

```
LangGraph = LangChain 的扩展，用于构建有状态的、多步骤的 Agent 工作流

类比：
• LangChain = 工具箱（单步调用 LLM/Tool）
• LangGraph = 工作流引擎（多步编排 + 状态管理）

适用场景：
• 归因分析（获取数据 → 分析 → 生成报告）
• 异常检测（检测异常 → 定位原因 → 生成结论）
• 多轮对话（理解意图 → 调用工具 → 返回结果）
```

### 10.2 安装 LangGraph

```powershell
pip install langgraph langchain langchain-core langchain-community
```

### 10.3 Agent 状态定义

```python
# app/agents/state.py
from typing import TypedDict, List, Optional, Literal
from datetime import date


class AttributionState(TypedDict):
    """归因分析 Agent 状态"""
    
    # 输入
    symbol: str                    # 股票代码
    start_date: date              # 开始日期
    end_date: date                # 结束日期
    
    # 中间状态
    klines: Optional[List]        # K线数据
    news: Optional[List]          # 新闻数据
    anomaly: Optional[dict]       # 异常信息
    attribution_result: Optional[dict]  # 归因结果
    
    # 输出
    report: Optional[str]          # 分析报告
    error: Optional[str]          # 错误信息


class AnomalyState(TypedDict):
    """异常检测 Agent 状态"""
    
    symbol: str
    start_date: date
    end_date: date
    klines: Optional[List]
    anomalies: List[dict]          # 检测到的异常列表
    is_anomaly: bool              # 是否有异常
```

### 10.4 Tool 定义

```python
# app/agents/tools/query_tools.py
from langchain_core.tools import tool
from typing import List
from datetime import date

from app.db.session import SessionLocal
from app.db.repositories.kline_repo import KLineRepository
from app.services.collector_service import CollectorService


@tool(description="查询股票K线历史数据")
def query_klines(
    symbol: str,
    start_date: str,
    end_date: str,
    limit: int = 100
) -> str:
    """
    查询指定股票指定日期范围的K线数据。
    
    Args:
        symbol: 股票代码，6位数字，如 "600519"
        start_date: 开始日期，格式 "YYYY-MM-DD"
        end_date: 结束日期，格式 "YYYY-MM-DD"
        limit: 最大返回条数，默认100条
        
    Returns:
        K线数据列表，包含日期、开盘价、收盘价、最高价、最低价、成交量等
    """
    db = SessionLocal()
    try:
        repo = KLineRepository(db)
        klines = repo.get_by_date_range(symbol, start_date, end_date)
        
        if not klines:
            return f"股票 {symbol} 在 {start_date} 至 {end_date} 期间无数据"
        
        # 限制返回条数
        klines = klines[-limit:]
        
        # 格式化输出
        lines = [f"股票 {symbol} K线数据（共 {len(klines)} 条）："]
        lines.append("-" * 80)
        lines.append(f"{'日期':<12} {'开盘':>10} {'收盘':>10} {'最高':>10} {'最低':>10} {'成交量':>12}")
        lines.append("-" * 80)
        
        for k in klines:
            lines.append(
                f"{str(k.date):<12} {k.open:>10.2f} {k.close:>10.2f} "
                f"{k.high:>10.2f} {k.low:>10.2f} {k.volume:>12.0f}"
            )
        
        return "\n".join(lines)
        
    finally:
        db.close()


@tool(description="查询股票相关新闻")
def query_news(
    symbol: str,
    days: int = 7
) -> str:
    """
    查询指定股票最近的新闻。
    
    Args:
        symbol: 股票代码，6位数字，如 "600519"
        days: 查询最近几天，默认7天
        
    Returns:
        新闻列表
    """
    db = SessionLocal()
    try:
        collector = CollectorService(db)
        count = collector.collect_news(symbol, days)
        
        # TODO: 查询数据库中的新闻
        return f"查询到 {symbol} 最近 {days} 天新闻 {count} 条"
        
    finally:
        db.close()


@tool(description="计算技术指标")
def calculate_indicators(
    prices: List[float]
) -> dict:
    """
    计算股票技术指标。
    
    Args:
        prices: 收盘价列表
        
    Returns:
        技术指标：MA5, MA10, MA20, 涨跌幅, 波动率等
    """
    if len(prices) < 5:
        return {"error": "数据不足，需要至少5条数据"}
    
    # 计算简单移动平均
    ma5 = sum(prices[-5:]) / 5
    ma10 = sum(prices[-10:]) / 10 if len(prices) >= 10 else None
    ma20 = sum(prices[-20:]) / 20 if len(prices) >= 20 else None
    
    # 计算涨跌幅
    change_pct = (prices[-1] - prices[-2]) / prices[-2] * 100 if len(prices) >= 2 else 0
    
    # 计算波动率（标准差）
    import statistics
    volatility = statistics.stdev(prices[-20:]) if len(prices) >= 20 else statistics.stdev(prices)
    
    return {
        "ma5": round(ma5, 2),
        "ma10": round(ma10, 2) if ma10 else None,
        "ma20": round(ma20, 2) if ma20 else None,
        "change_pct": round(change_pct, 2),
        "volatility": round(volatility, 2),
        "latest_price": prices[-1]
    }
```

### 10.5 节点定义

```python
# app/agents/nodes/anomaly_node.py
from typing import Annotated, Literal
from langgraph.graph import StateGraph, END

from app.agents.state import AnomalyState
from app.agents.tools.query_tools import query_klines, calculate_indicators


def detect_anomaly(state: AnomalyState) -> AnomalyState:
    """异常检测节点"""
    
    # 1. 获取K线数据
    kline_data = query_klines.invoke({
        "symbol": state["symbol"],
        "start_date": str(state["start_date"]),
        "end_date": str(state["end_date"]),
        "limit": 100
    })
    
    # 2. 提取价格列表
    # 实际应解析 kline_data，这里简化
    prices = []  # 从 kline_data 解析
    
    # 3. 计算指标
    indicators = calculate_indicators.invoke({"prices": prices})
    
    # 4. 异常检测逻辑
    anomalies = []
    
    # 检测1：涨跌幅异常（超过5%）
    if abs(indicators.get("change_pct", 0)) > 5:
        anomalies.append({
            "type": "price_change",
            "severity": "high" if abs(indicators["change_pct"]) > 10 else "medium",
            "value": indicators["change_pct"],
            "description": f"涨跌幅异常：{indicators['change_pct']}%"
        })
    
    # 检测2：波动率异常
    if indicators.get("volatility", 0) > indicators.get("ma20", 0) * 0.05:
        anomalies.append({
            "type": "high_volatility",
            "severity": "medium",
            "value": indicators["volatility"],
            "description": "波动率异常偏高"
        })
    
    return {
        **state,
        "klines": kline_data,
        "anomalies": anomalies,
        "is_anomaly": len(anomalies) > 0
    }


def should_escalate(state: AnomalyState) -> Literal["generate_report", "__end__"]:
    """判断是否需要生成报告"""
    if state["is_anomaly"]:
        return "generate_report"
    return END


def generate_report(state: AnomalyState) -> AnomalyState:
    """生成异常报告"""
    
    # TODO: 调用 LLM 生成报告
    report = f"""# 异常检测报告

股票：{state['symbol']}
日期：{state['start_date']} 至 {state['end_date']}

## 检测到的异常

{chr(10).join([f"- {a['description']}" for a in state['anomalies']])}

## 建议

建议进一步分析异常原因。
"""
    
    return {**state, "report": report}
```

### 10.6 构建工作流图

```python
# app/agents/graphs/anomaly_graph.py
from langgraph.graph import StateGraph, END
from app.agents.state import AnomalyState
from app.agents.nodes.anomaly_node import detect_anomaly, should_escalate, generate_report


def build_anomaly_graph():
    """构建异常检测工作流"""
    
    workflow = StateGraph(AnomalyState)
    
    # 添加节点
    workflow.add_node("detect", detect_anomaly)
    workflow.add_node("report", generate_report)
    
    # 设置入口
    workflow.set_entry_point("detect")
    
    # 添加条件边
    workflow.add_conditional_edges(
        "detect",
        should_escalate,
        {
            "generate_report": "report",
            END: END
        }
    )
    
    # 添加结束边
    workflow.add_edge("report", END)
    
    return workflow.compile()


# 创建全局实例
anomaly_graph = build_anomaly_graph()


# 使用示例
async def run_anomaly_detection(symbol: str, start_date: str, end_date: str):
    """运行异常检测"""
    
    result = await anomaly_graph.ainvoke({
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "klines": None,
        "anomalies": [],
        "is_anomaly": False
    })
    
    return result
```

### 10.7 接入 API

```python
# app/api/v1/analyze.py

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import date

from app.agents.graphs.anomaly_graph import anomaly_graph

router = APIRouter()


class AnomalyAnalyzeRequest(BaseModel):
    symbol: str
    start_date: date
    end_date: date


@router.post("/anomaly", summary="异常检测分析")
async def analyze_anomaly(request: AnomalyAnalyzeRequest):
    """
    对指定股票的K线数据进行异常检测分析
    
    - symbol: 股票代码
    - start_date: 开始日期
    - end_date: 结束日期
    """
    
    result = await anomaly_graph.ainvoke({
        "symbol": request.symbol,
        "start_date": request.start_date,
        "end_date": request.end_date,
        "klines": None,
        "anomalies": [],
        "is_anomaly": False
    })
    
    return {
        "symbol": result["symbol"],
        "is_anomaly": result["is_anomaly"],
        "anomalies": result["anomalies"],
        "report": result.get("report")
    }
```

---

## 附录 A：快速启动脚本

### A.1 Windows 启动脚本

```powershell
# backend/start.bat
@echo off

cd /d "%~dp0"

echo.
echo ========================================
echo   归因分析平台后端启动
echo ========================================
echo.

REM 激活虚拟环境
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [错误] 虚拟环境不存在，请先运行 init.bat
    pause
    exit /b 1
)

REM 检查依赖
pip show fastapi > nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 依赖未安装，正在安装...
    pip install -r requirements.txt
)

REM 启动服务
echo.
echo 启动服务...
echo 文档地址: http://localhost:8000/docs
echo.

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### A.2 初始化脚本

```powershell
# backend/init.bat
@echo off

cd /d "%~dp0"

echo.
echo ========================================
echo   初始化项目环境
echo ========================================
echo.

REM 创建虚拟环境
if not exist venv (
    echo [1/5] 创建虚拟环境...
    python -m venv venv
) else (
    echo [跳过] 虚拟环境已存在
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 升级 pip
echo [2/5] 升级 pip...
python -m pip install --upgrade pip

REM 安装依赖
echo [3/5] 安装依赖（可能需要几分钟）...
pip install -r requirements.txt

REM 初始化数据库
echo [4/5] 初始化数据库...
alembic upgrade head

echo [5/5] 环境准备完成！

echo.
echo ========================================
echo   下一步：
echo   1. 配置 .env 文件
echo   2. 运行 start.bat 启动服务
echo ========================================
echo.

pause
```

### A.3 Docker 部署

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 附录 B：常见问题

### B.1 虚拟环境问题

```powershell
# 问题：pip install 报错 "externally-managed-environment"
# 解决：使用虚拟环境
python -m venv venv
.\venv\Scripts\activate

# 或者用 --user 安装（不推荐）
pip install --user 包名
```

### B.2 数据库连接问题

```python
# 问题：连接 MySQL 报错 "Authentication plugin 'caching_sha2_password'"
# 解决：升级 pymysql 或修改用户认证方式

# 方式1：升级 pymysql
pip install --upgrade pymysql

# 方式2：修改 MySQL 用户认证
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'password';
FLUSH PRIVILEGES;
```

### B.3 AkShare 访问限制

```python
# 问题：AkShare 返回空数据或报错
# 解决：添加请求延迟

import time
time.sleep(1)  # 每次请求间隔1秒

# 或使用代理
ak.stock_zh_a_hist(symbol="600519", proxy="http://127.0.0.1:7890")
```

### B.4 中文编码问题

```python
# 问题：MySQL 存储中文乱码
# 解决1：连接字符串加 charset
DATABASE_URL = "mysql+pymysql://.../?charset=utf8mb4"

# 解决2：Python 文件开头加编码声明
# -*- coding: utf-8 -*-
```

### B.5 异步与同步混用

```python
# 问题：在 async 函数中调用同步代码卡住
# 解决：用 run_in_executor 包装

async def fetch_data():
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, sync_function)
    return result
```

---

## 附录 C：资源链接

| 资源 | 链接 |
|------|------|
| FastAPI 官方文档 | https://fastapi.tiangolo.com/zh/ |
| SQLAlchemy 文档 | https://docs.sqlalchemy.org/ |
| AkShare 文档 | https://akshare.akfamily.xyz/ |
| LangGraph 文档 | https://langchain-ai.github.io/langgraph/ |
| Pydantic 文档 | https://docs.pydantic.dev/ |
| Python 教程 | https://docs.python.org/zh-cn/3/tutorial/ |

---

*文档版本：v1.0.0*
*最后更新：2026-06-25*
*作者：基于 Java Spring Boot 经验的 FastAPI 开发指南*
