# Step 05: CRUD 操作 - 增删改查综合示例

## 学习目标
实现完整的 CRUD API，掌握数据库操作的完整流程

## 概念速览

```
CRUD = Create(创建) + Read(读取) + Update(更新) + Delete(删除)

路由设计（RESTful 风格）
├── GET    /stocks          → 列表
├── GET    /stocks/{code}   → 详情
├── POST   /stocks          → 创建
├── PUT    /stocks/{code}   → 更新
├── DELETE /stocks/{code}   → 删除
```

## 任务

### 任务 1: 定义统一的响应模型

创建 `demo_05_crud.py`：

```python
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from demo_04_database import engine, SessionLocal, Base, Stock, AnomalyRecord, get_db

app = FastAPI()

# ============ Pydantic 响应模型 ============

class StockBase(BaseModel):
    """股票基础模型"""
    code: str
    name: str
    price: float = 0.0
    change: float = 0.0
    volume: int = 0

class StockCreate(StockBase):
    """创建股票的请求模型"""
    pass

class StockUpdate(BaseModel):
    """更新股票的请求模型"""
    price: Optional[float] = None
    change: Optional[float] = None
    volume: Optional[int] = None

class StockResponse(StockBase):
    """股票响应模型"""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}

class StockListResponse(BaseModel):
    """股票列表响应"""
    total: int
    page: int
    page_size: int
    items: List[StockResponse]

class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str
    success: bool = True

# ============ 通用响应工具 ============

def success_response(message: str):
    return MessageResponse(message=message, success=True)

def error_response(message: str, status_code: int = 400):
    raise HTTPException(status_code=status_code, detail=message)
```

### 任务 2: 读取操作 (Read)

```python
# ============ 读取操作 ============

@app.get("/stocks", response_model=StockListResponse)
def list_stocks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    market: Optional[str] = Query(None, description="市场筛选"),
    min_price: Optional[float] = Query(None, ge=0, description="最低价格"),
    max_price: Optional[float] = Query(None, gt=0, description="最高价格"),
    sort_by: str = Query("code", description="排序字段"),
    order: str = Query("asc", description="排序方向: asc/desc"),
    db: Session = Depends(get_db)
):
    """获取股票列表（分页、筛选、排序）"""
    
    # 构建查询
    query = db.query(Stock)
    
    # 筛选
    if market:
        if market == "sh":
            query = query.filter(Stock.code.startswith("6"))
        elif market == "sz":
            query = query.filter(Stock.code.startswith(("0", "3")))
    
    if min_price is not None:
        query = query.filter(Stock.price >= min_price)
    
    if max_price is not None:
        query = query.filter(Stock.price <= max_price)
    
    # 排序
    sort_column = getattr(Stock, sort_by, Stock.code)
    if order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(sort_column)
    
    # 获取总数
    total = query.count()
    
    # 分页
    offset = (page - 1) * page_size
    stocks = query.offset(offset).limit(page_size).all()
    
    return StockListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[StockResponse.model_validate(s) for s in stocks]
    )

@app.get("/stocks/{code}", response_model=StockResponse)
def get_stock(code: str, db: Session = Depends(get_db)):
    """获取单个股票详情"""
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        error_response(f"股票 {code} 不存在", 404)
    return StockResponse.model_validate(stock)

@app.get("/stocks/{code}/exists")
def check_stock_exists(code: str, db: Session = Depends(get_db)):
    """检查股票是否存在"""
    exists = db.query(Stock).filter(Stock.code == code).first() is not None
    return {"exists": exists, "code": code}
```

### 任务 3: 创建操作 (Create)

```python
# ============ 创建操作 ============

@app.post("/stocks", response_model=StockResponse, status_code=201)
def create_stock(stock_data: StockCreate, db: Session = Depends(get_db)):
    """创建新股票"""
    # 检查是否已存在
    existing = db.query(Stock).filter(Stock.code == stock_data.code).first()
    if existing:
        error_response(f"股票 {stock_data.code} 已存在", 409)
    
    # 创建记录
    stock = Stock(
        code=stock_data.code,
        name=stock_data.name,
        price=stock_data.price,
        change=stock_data.change,
        volume=stock_data.volume
    )
    
    db.add(stock)
    db.commit()
    db.refresh(stock)
    
    return StockResponse.model_validate(stock)

@app.post("/stocks/batch", response_model=List[StockResponse], status_code=201)
def create_stocks_batch(stocks_data: List[StockCreate], db: Session = Depends(get_db)):
    """批量创建股票"""
    created = []
    errors = []
    
    for stock_data in stocks_data:
        existing = db.query(Stock).filter(Stock.code == stock_data.code).first()
        if existing:
            errors.append(f"股票 {stock_data.code} 已存在，跳过")
            continue
        
        stock = Stock(
            code=stock_data.code,
            name=stock_data.name,
            price=stock_data.price,
            change=stock_data.change,
            volume=stock_data.volume
        )
        db.add(stock)
        created.append(stock)
    
    db.commit()
    
    return [StockResponse.model_validate(s) for s in created]
```

### 任务 4: 更新操作 (Update)

```python
# ============ 更新操作 ============

@app.put("/stocks/{code}", response_model=StockResponse)
def update_stock(
    code: str,
    update_data: StockUpdate,
    db: Session = Depends(get_db)
):
    """更新股票信息"""
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        error_response(f"股票 {code} 不存在", 404)
    
    # 只更新提供的字段
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(stock, field, value)
    
    stock.updated_at = datetime.now()
    
    db.commit()
    db.refresh(stock)
    
    return StockResponse.model_validate(stock)

@app.patch("/stocks/{code}/price")
def update_price(
    code: str,
    new_price: float = Query(..., gt=0, description="新价格"),
    new_change: Optional[float] = Query(None, description="涨跌额"),
    db: Session = Depends(get_db)
):
    """快速更新价格（专用接口）"""
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        error_response(f"股票 {code} 不存在", 404)
    
    stock.price = new_price
    if new_change is not None:
        stock.change = new_change
    stock.updated_at = datetime.now()
    
    db.commit()
    
    return success_response(f"股票 {code} 价格已更新为 {new_price}")
```

### 任务 5: 删除操作 (Delete)

```python
# ============ 删除操作 ============

@app.delete("/stocks/{code}")
def delete_stock(code: str, db: Session = Depends(get_db)):
    """删除股票"""
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        error_response(f"股票 {code} 不存在", 404)
    
    db.delete(stock)
    db.commit()
    
    return success_response(f"股票 {code} 已删除")

@app.delete("/stocks")
def delete_all_stocks(db: Session = Depends(get_db)):
    """清空所有股票（谨慎使用）"""
    count = db.query(Stock).delete()
    db.commit()
    
    return success_response(f"已删除 {count} 条记录")
```

### 任务 6: 统计接口

```python
# ============ 统计接口 ============

@app.get("/stocks/stats/summary")
def get_stocks_summary(db: Session = Depends(get_db)):
    """获取股票统计摘要"""
    total_count = db.query(Stock).count()
    
    # 价格统计
    from sqlalchemy import func
    
    price_stats = db.query(
        func.avg(Stock.price).label("avg_price"),
        func.min(Stock.price).label("min_price"),
        func.max(Stock.price).label("max_price"),
        func.sum(Stock.volume).label("total_volume")
    ).first()
    
    # 涨跌统计
    rising = db.query(Stock).filter(Stock.change > 0).count()
    falling = db.query(Stock).filter(Stock.change < 0).count()
    flat = db.query(Stock).filter(Stock.change == 0).count()
    
    return {
        "total_stocks": total_count,
        "price": {
            "avg": round(price_stats.avg_price or 0, 2),
            "min": price_stats.min_price or 0,
            "max": price_stats.max_price or 0,
        },
        "total_volume": price_stats.total_volume or 0,
        "changes": {
            "rising": rising,
            "falling": falling,
            "flat": flat
        }
    }
```

## 测试

```bash
# 创建股票
curl -X POST "http://localhost:8000/stocks" \
  -H "Content-Type: application/json" \
  -d '{"code": "601318", "name": "中国平安", "price": 50.0, "change": 1.5, "volume": 2000000}'

# 获取列表
curl "http://localhost:8000/stocks?page=1&page_size=5"

# 获取详情
curl "http://localhost:8000/stocks/600519"

# 更新价格
curl -X PUT "http://localhost:8000/stocks/600519" \
  -H "Content-Type: application/json" \
  -d '{"price": 1600.0}'

# 删除
curl -X DELETE "http://localhost:8000/stocks/601318"

# 统计
curl "http://localhost:8000/stocks/stats/summary"
```

## 下一步
阅读 `../docs/analysis/05_crud_operations.md` 深入理解
