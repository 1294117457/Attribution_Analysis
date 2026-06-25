# Python 后端开发指南

> 本文档专注于 **A股数据接入 + PostgreSQL 持久化** 的核心实现

---

## 目录

1. [环境准备](#1-环境准备)
2. [项目初始化](#2-项目初始化)
3. [数据库配置](#3-数据库配置)
4. [数据采集：AkShare](#4-数据采集akshare)
5. [API 接口](#5-api-接口)
6. [快速启动](#6-快速启动)

---

## 1. 环境准备

### 1.1 安装 Python

```bash
# Windows: https://www.python.org/downloads/
# 验证安装
python --version
pip --version
```

### 1.2 pip 换源（国内加速）

```bash
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 2. 项目初始化

### 2.1 创建项目

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

### 2.2 安装依赖

```bash
pip install fastapi uvicorn sqlalchemy asyncpg alembic \
    akshare pandas pydantic-settings redis httpx
```

### 2.3 配置环境变量

```env
# .env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/attribution
DATABASE_URL_ASYNC=postgresql+asyncpg://postgres:postgres@localhost:5432/attribution
REDIS_URL=redis://localhost:6379/0
```

### 2.4 项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py           # 入口
│   ├── config.py         # 配置
│   ├── models/           # SQLAlchemy 模型
│   │   └── kline.py
│   ├── schemas/          # Pydantic DTO
│   │   └── kline.py
│   ├── services/         # 业务逻辑
│   │   └── collector.py  # AkShare 采集
│   └── api/v1/
│       └── klines.py     # API 路由
├── scripts/
│   └── init_db.py        # 数据库初始化
├── alembic/              # 迁移
└── requirements.txt
```

---

## 3. 数据库配置

### 3.1 配置模块

```python
# app/config.py
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/attribution"
    DATABASE_URL_ASYNC: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/attribution"
    REDIS_URL: str = "redis://localhost:6379/0"
    DEBUG: bool = True

    class Config:
        env_file = BASE_DIR / ".env"

settings = Settings()
```

### 3.2 数据库连接

```python
# app/db/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# 同步引擎
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# 异步引擎
async_engine = create_async_engine(settings.DATABASE_URL_ASYNC, pool_pre_ping=True)

AsyncSessionLocal = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# app/db/session.py
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

### 3.3 数据模型

```python
# app/models/kline.py
from sqlalchemy import Column, Integer, String, Float, Date, Index, JSON
from app.db.database import Base

class StockKline(Base):
    __tablename__ = "stock_klines"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    amount = Column(Float)
    change_pct = Column(Float)
    indicators = Column(JSON, default={})  # 技术指标缓存

    __table_args__ = (Index('idx_symbol_date', 'symbol', 'trade_date', unique=True),)
```

### 3.4 数据库初始化

```bash
# 初始化 PostgreSQL（Docker）
docker run -d --name attribution-postgres \
  -e POSTGRES_DB=attribution \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# 初始化表结构
cd backend
alembic upgrade head
```

---

## 4. 数据采集：AkShare

### 4.1 采集服务

```python
# app/services/collector.py
import akshare as ak
import pandas as pd
from datetime import date, timedelta
from typing import List
from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.models.kline import StockKline


async def collect_klines(symbol: str, start_date: date, end_date: date) -> int:
    """
    从 AkShare 采集 K 线数据并存入数据库
    """
    # 1. 调用 AkShare（同步操作，需在线程池执行）
    import asyncio
    loop = asyncio.get_event_loop()

    df = await loop.run_in_executor(
        None,
        lambda: ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
            adjust="qfq"
        )
    )

    if df is None or df.empty:
        return 0

    # 2. 转换并批量写入
    klines = []
    for _, row in df.iterrows():
        kline = StockKline(
            symbol=str(row['股票代码']),
            trade_date=pd.to_datetime(row['日期']).date(),
            open=float(row['开盘']),
            high=float(row['最高']),
            low=float(row['最低']),
            close=float(row['收盘']),
            volume=float(row['成交量']),
            amount=float(row['成交额']),
            change_pct=float(row['涨跌幅']) if pd.notna(row.get('涨跌幅')) else None,
        )
        klines.append(kline)

    # 3. 写入数据库（使用 ON CONFLICT 避免重复）
    async with AsyncSessionLocal() as session:
        for kline in klines:
            session.add(kline)
        await session.commit()

    return len(klines)


async def collect_batch(symbols: List[str], days: int = 365) -> dict:
    """批量采集多只股票"""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    results = {"success": 0, "failed": 0}
    for symbol in symbols:
        try:
            count = await collect_klines(symbol, start_date, end_date)
            if count > 0:
                results["success"] += 1
            await asyncio.sleep(1)  # 避免频率限制
        except Exception as e:
            print(f"采集 {symbol} 失败: {e}")
            results["failed"] += 1

    return results
```

### 4.2 命令行脚本

```python
# scripts/collect_data.py
import asyncio
import sys
from datetime import date, timedelta
from app.services.collector import collect_klines, collect_batch

async def main():
    if len(sys.argv) < 2:
        print("用法: python -m scripts.collect_data <股票代码>")
        print("示例: python -m scripts.collect_data 600519")
        return

    symbol = sys.argv[1]
    end_date = date.today()
    start_date = end_date - timedelta(days=365)

    print(f"采集 {symbol} 从 {start_date} 到 {end_date}...")
    count = await collect_klines(symbol, start_date, end_date)
    print(f"完成！采集 {count} 条数据")

if __name__ == "__main__":
    asyncio.run(main())
```

```bash
# 使用示例
python -m scripts.collect_data 600519  # 采集茅台
python -m scripts.collect_data 000858  # 采集五粮液
```

---

## 5. API 接口

### 5.1 入口文件

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import router as api_v1

app = FastAPI(title="归因分析 API", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(api_v1.router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### 5.2 K 线 API

```python
# app/api/v1/klines.py
from fastapi import APIRouter, Depends, Query
from typing import List
from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.kline import StockKline

router = APIRouter()


@router.get("/klines")
async def get_klines(
    symbol: str = Query(..., description="股票代码"),
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    db: AsyncSession = Depends(get_db)
):
    """查询 K 线数据"""
    stmt = select(StockKline).where(
        StockKline.symbol == symbol,
        StockKline.trade_date >= start_date,
        StockKline.trade_date <= end_date
    ).order_by(StockKline.trade_date)

    result = await db.execute(stmt)
    klines = result.scalars().all()

    return {
        "symbol": symbol,
        "count": len(klines),
        "data": [
            {
                "date": k.trade_date,
                "open": k.open,
                "high": k.high,
                "low": k.low,
                "close": k.close,
                "volume": k.volume,
                "change_pct": k.change_pct
            }
            for k in klines
        ]
    }


@router.post("/klines/collect")
async def collect_klines(
    symbol: str = Query(..., description="股票代码"),
    days: int = Query(365, description="采集天数"),
    db: AsyncSession = Depends(get_db)
):
    """采集 K 线数据"""
    from app.services.collector import collect_klines
    from datetime import timedelta

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    count = await collect_klines(symbol, start_date, end_date)

    return {"symbol": symbol, "collected": count}
```

### 5.3 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5.4 API 文档

启动后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 6. 快速启动

### 6.1 一键启动（Docker）

```bash
# 启动 PostgreSQL
docker run -d --name attribution-postgres \
  -e POSTGRES_DB=attribution \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# 启动后端
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 6.2 采集测试

```bash
# 采集贵州茅台数据
curl "http://localhost:8000/api/v1/klines/collect?symbol=600519&days=30"

# 查询数据
curl "http://localhost:8000/api/v1/klines?symbol=600519&start_date=2024-01-01&end_date=2024-06-25"
```

### 6.3 下一步

| 功能 | 文档位置 |
|------|----------|
| 技术指标计算 | `docs/architecture.md` |
| 异常检测算法 | `docs/architecture.md` |
| LangGraph Agent | 后续章节 |
| pgvector 经验系统 | 后续章节 |

---

## 常见问题

### Q: AkShare 返回空数据
```python
# 添加延迟避免频率限制
import time
time.sleep(1)
```

### Q: PostgreSQL 连接失败
```bash
# 检查是否运行
docker ps | grep postgres

# 启动容器
docker start attribution-postgres
```

### Q: 中文乱码
```python
# 确保数据库编码为 UTF-8
# 连接字符串通常自动处理
```

---

*文档版本：v4.0 | 最后更新：2026-06-25*
