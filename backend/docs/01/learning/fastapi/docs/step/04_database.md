# Step 04: 数据库连接 - SQLAlchemy 基础

## 学习目标
掌握 SQLAlchemy 的基本用法，连接 SQLite/MySQL 数据库

## 概念速览

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. 创建连接
engine = create_engine("sqlite:///./stocks.db")

# 2. 创建会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. 定义模型
Base = declarative_base()

class Stock(Base):
    __tablename__ = "stocks"
    
    code = Column(String, primary_key=True, index=True)
    name = Column(String)
    price = Column(Float)

# 4. 创建表
Base.metadata.create_all(bind=engine)
```

## 任务

### 任务 1: 基本数据库设置

创建 `demo_04_database.py`：

```python
from fastapi import FastAPI
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from datetime import datetime
from typing import Generator

app = FastAPI()

# 1. 数据库配置
DATABASE_URL = "sqlite:///./stocks.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite 专用
)

# 2. 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. 定义基类
Base = declarative_base()

# 4. 定义数据模型
class Stock(Base):
    __tablename__ = "stocks"
    
    code = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, default=0.0)
    change = Column(Float, default=0.0)
    volume = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class AnomalyRecord(Base):
    __tablename__ = "anomaly_records"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    stock_code = Column(String, index=True)
    date = Column(String)
    anomaly_type = Column(String)  # price, volume
    value = Column(Float)
    threshold = Column(Float)
    severity = Column(String)  # low, medium, high
    created_at = Column(DateTime, default=datetime.now)

# 5. 创建所有表
Base.metadata.create_all(bind=engine)

# 6. 获取数据库会话的依赖
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 健康检查
@app.get("/health")
def health_check():
    return {"status": "healthy", "database": "connected"}
```

### 任务 2: 初始化数据

```python
# 7. 初始化示例数据
@app.on_event("startup")
def init_db():
    """启动时初始化数据库"""
    db = SessionLocal()
    try:
        # 检查是否已有数据
        existing = db.query(Stock).first()
        if not existing:
            # 添加示例股票
            stocks = [
                Stock(code="600519", name="贵州茅台", price=1500.0, change=2.5, volume=1000000),
                Stock(code="000858", name="五粮液", price=150.0, change=-1.2, volume=500000),
                Stock(code="600036", name="招商银行", price=35.0, change=0.8, volume=2000000),
            ]
            db.add_all(stocks)
            db.commit()
            print("数据库初始化完成")
        else:
            print("数据库已有数据")
    finally:
        db.close()
```

### 任务 3: 数据库 CRUD 操作

```python
# ============ 增删改查示例 ============

@app.get("/db/stocks")
def list_stocks(db: Session = Depends(get_db)):
    """查询所有股票"""
    stocks = db.query(Stock).all()
    return [
        {
            "code": s.code,
            "name": s.name,
            "price": s.price,
            "change": s.change
        }
        for s in stocks
    ]

@app.get("/db/stocks/{code}")
def get_stock(code: str, db: Session = Depends(get_db)):
    """根据代码查询股票"""
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        return {"error": "股票不存在"}
    return {
        "code": stock.code,
        "name": stock.name,
        "price": stock.price,
        "change": stock.change,
        "volume": stock.volume
    }

@app.post("/db/stocks")
def create_stock(
    code: str,
    name: str,
    price: float,
    db: Session = Depends(get_db)
):
    """创建股票"""
    # 检查是否已存在
    existing = db.query(Stock).filter(Stock.code == code).first()
    if existing:
        return {"error": "股票已存在"}
    
    stock = Stock(code=code, name=name, price=price)
    db.add(stock)
    db.commit()
    db.refresh(stock)
    return {"created": True, "code": stock.code}

@app.put("/db/stocks/{code}")
def update_stock(
    code: str,
    price: float,
    change: float,
    volume: int,
    db: Session = Depends(get_db)
):
    """更新股票"""
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        return {"error": "股票不存在"}
    
    stock.price = price
    stock.change = change
    stock.volume = volume
    stock.updated_at = datetime.now()
    
    db.commit()
    db.refresh(stock)
    return {"updated": True, "code": stock.code}

@app.delete("/db/stocks/{code}")
def delete_stock(code: str, db: Session = Depends(get_db)):
    """删除股票"""
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        return {"error": "股票不存在"}
    
    db.delete(stock)
    db.commit()
    return {"deleted": True, "code": code}
```

## 依赖注入

需要添加导入：

```python
from fastapi import Depends
```

## 测试

```bash
# 启动服务
uvicorn demo_04_database:app --reload

# 测试数据库
curl http://localhost:8000/health
curl http://localhost:8000/db/stocks
curl http://localhost:8000/db/stocks/600519
curl -X POST "http://localhost:8000/db/stocks?code=601318&name=中国平安&price=50.0"
```

## 下一步
阅读 `../docs/analysis/04_database.md` 深入理解
