# CRUD 操作详解

## 一、RESTful API 设计原则

### 什么是 RESTful？

```
REST = Representational State Transfer
一种设计风格，不是标准

核心原则：
├── 用 URL 表示资源（名词）
├── 用 HTTP 方法表示操作
└── 用状态码表示结果
```

### CRUD 映射

| 操作 | HTTP 方法 | URL | 状态码 |
|------|-----------|-----|--------|
| 创建 | POST | /stocks | 201 |
| 读取 | GET | /stocks, /stocks/{id} | 200 |
| 更新 | PUT/PATCH | /stocks/{id} | 200 |
| 删除 | DELETE | /stocks/{id} | 204 |

### 路由命名规范

```python
# ✅ 推荐：RESTful 风格
GET    /stocks              # 列表
GET    /stocks/{code}       # 详情
POST   /stocks              # 创建
PUT    /stocks/{code}       # 全量更新
PATCH  /stocks/{code}      # 部分更新
DELETE /stocks/{code}       # 删除

# ❌ 不推荐：行为式命名
GET    /getStocks           # 行为在 URL 中
POST   /createStock         # 应该用 POST
POST   /deleteStock/{code}  # 应该用 DELETE
```

## 二、创建 (Create)

### POST 请求

```python
@app.post("/stocks", status_code=201)
def create_stock(stock: StockCreate, db: Session = Depends(get_db)):
    # 1. 检查是否已存在
    existing = db.query(Stock).filter(Stock.code == stock.code).first()
    if existing:
        raise HTTPException(status_code=409, detail="股票已存在")
    
    # 2. 创建对象
    db_stock = Stock(
        code=stock.code,
        name=stock.name,
        price=stock.price
    )
    
    # 3. 保存
    db.add(db_stock)
    db.commit()
    db.refresh(db_stock)
    
    return db_stock
```

### 状态码

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 200 | OK | GET/PUT/PATCH 成功 |
| 201 | Created | POST 创建成功 |
| 204 | No Content | DELETE 成功 |
| 400 | Bad Request | 请求参数错误 |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 资源冲突（已存在） |
| 422 | Unprocessable Entity | 验证失败 |

## 三、读取 (Read)

### 获取单个资源

```python
@app.get("/stocks/{code}")
def get_stock(code: str, db: Session = Depends(get_db)):
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        raise HTTPException(status_code=404, detail="股票不存在")
    return stock
```

### 获取资源列表

```python
@app.get("/stocks")
def list_stocks(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    stocks = db.query(Stock).offset(skip).limit(limit).all()
    total = db.query(Stock).count()
    return {"total": total, "items": stocks}
```

### 高级查询

```python
from sqlalchemy import and_, or_, func

@app.get("/stocks")
def search_stocks(
    # 精确匹配
    market: Optional[str] = None,
    
    # 范围查询
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    
    # 模糊查询
    name_contains: Optional[str] = None,
    
    # 分页
    page: int = 1,
    page_size: int = 20,
    
    # 排序
    sort_by: str = "code",
    order: str = "asc",
    
    db: Session = Depends(get_db)
):
    query = db.query(Stock)
    
    # 组合条件
    conditions = []
    
    if market:
        if market == "sh":
            conditions.append(Stock.code.like("6%"))
        elif market == "sz":
            conditions.append(Stock.code.like(("0%", "3%")))
    
    if min_price is not None:
        conditions.append(Stock.price >= min_price)
    
    if max_price is not None:
        conditions.append(Stock.price <= max_price)
    
    if name_contains:
        conditions.append(Stock.name.ilike(f"%{name_contains}%"))
    
    # 应用条件
    if conditions:
        query = query.filter(and_(*conditions))
    
    # 排序
    sort_column = getattr(Stock, sort_by)
    if order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column)
    
    # 总数
    total = query.count()
    
    # 分页
    offset = (page - 1) * page_size
    stocks = query.offset(offset).limit(page_size).all()
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": stocks
    }
```

## 四、更新 (Update)

### PUT vs PATCH

```
PUT   → 全量更新：必须提供所有字段
PATCH → 部分更新：只更新提供的字段
```

### 全量更新 (PUT)

```python
@app.put("/stocks/{code}")
def update_stock_full(
    code: str,
    stock_update: StockUpdate,
    db: Session = Depends(get_db)
):
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        raise HTTPException(status_code=404, detail="股票不存在")
    
    # 全量更新：直接替换
    stock.code = stock_update.code
    stock.name = stock_update.name
    stock.price = stock_update.price
    
    db.commit()
    db.refresh(stock)
    return stock
```

### 部分更新 (PATCH)

```python
@app.patch("/stocks/{code}")
def update_stock_partial(
    code: str,
    stock_update: StockUpdate,
    db: Session = Depends(get_db)
):
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        raise HTTPException(status_code=404, detail="股票不存在")
    
    # 部分更新：只更新提供的字段
    update_data = stock_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(stock, field, value)
    
    db.commit()
    db.refresh(stock)
    return stock
```

## 五、删除 (Delete)

### 基本删除

```python
@app.delete("/stocks/{code}", status_code=204)
def delete_stock(code: str, db: Session = Depends(get_db)):
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        raise HTTPException(status_code=404, detail="股票不存在")
    
    db.delete(stock)
    db.commit()
    # 204 No Content 不返回 body
    return None
```

### 软删除 vs 硬删除

```python
# 软删除（推荐）：不真正删除，标记状态
class Stock(Base):
    __tablename__ = "stocks"
    
    code = Column(String, primary_key=True)
    name = Column(String)
    is_deleted = Column(Boolean, default=False)  # 软删除标记
    deleted_at = Column(DateTime, nullable=True)

@app.delete("/stocks/{code}")
def soft_delete_stock(code: str, db: Session = Depends(get_db)):
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        raise HTTPException(status_code=404, detail="股票不存在")
    
    stock.is_deleted = True
    stock.deleted_at = datetime.now()
    db.commit()
    
    return {"message": "删除成功"}
```

## 六、异常处理

### HTTPException

```python
from fastapi import HTTPException

@app.get("/stocks/{code}")
def get_stock(code: str, db: Session = Depends(get_db)):
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        raise HTTPException(
            status_code=404,
            detail=f"股票 {code} 不存在"
        )
    return stock
```

### 自定义异常处理器

```python
class StockNotFoundException(Exception):
    def __init__(self, code: str):
        self.code = code
        self.message = f"股票 {code} 不存在"

@app.exception_handler(StockNotFoundException)
async def stock_not_found_handler(request, exc: StockNotFoundException):
    return JSONResponse(
        status_code=404,
        content={"error": exc.message, "code": exc.code}
    )

# 使用
@app.get("/stocks/{code}")
def get_stock(code: str, db: Session = Depends(get_db)):
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        raise StockNotFoundException(code)
    return stock
```

## 七、分页实现

### 方式1：偏移量分页

```python
def get_paginated_items(page: int, page_size: int, db: Session):
    offset = (page - 1) * page_size
    items = db.query(Stock).offset(offset).limit(page_size).all()
    total = db.query(Stock).count()
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }
```

### 方式2：游标分页（适合大数据）

```python
def get_cursor_paginated_items(cursor: Optional[str], limit: int, db: Session):
    query = db.query(Stock)
    
    if cursor:
        query = query.filter(Stock.code > cursor)
    
    items = query.order_by(Stock.code).limit(limit + 1).all()
    
    has_more = len(items) > limit
    if has_more:
        items = items[:-1]
    
    next_cursor = items[-1].code if has_more else None
    
    return {
        "items": items,
        "next_cursor": next_cursor,
        "has_more": has_more
    }
```

## 八、事务管理

### 基本事务

```python
@app.post("/stocks/batch")
def create_stocks_batch(stocks: List[StockCreate], db: Session = Depends(get_db)):
    try:
        for stock_data in stocks:
            stock = Stock(**stock_data.model_dump())
            db.add(stock)
        
        db.commit()  # 一次性提交
        return {"created": len(stocks)}
    except Exception as e:
        db.rollback()  # 出错回滚
        raise HTTPException(status_code=500, detail=str(e))
```

### 使用上下文管理器

```python
@app.post("/stocks/batch")
def create_stocks_batch(stocks: List[StockCreate], db: Session = Depends(get_db)):
    with db.begin():  # 自动处理 commit/rollback
        for stock_data in stocks:
            db.add(Stock(**stock_data.model_dump()))
    
    return {"created": len(stocks)}
```

## 九、常见问题

### 1. 并发冲突

```python
# 乐观锁：使用版本号
class Stock(Base):
    __tablename__ = "stocks"
    code = Column(String, primary_key=True)
    version = Column(Integer, default=0)

@app.put("/stocks/{code}")
def update_stock(code: str, update: StockUpdate, db: Session = Depends(get_db)):
    stock = db.query(Stock).filter(Stock.code == code).first()
    
    # 检查版本
    if stock.version != update.expected_version:
        raise HTTPException(status_code=409, detail="数据已被修改")
    
    stock.version += 1
    # 更新其他字段...
```

### 2. 性能优化

```python
# 使用索引
class Stock(Base):
    code = Column(String, primary_key=True, index=True)
    market = Column(String, index=True)  # 常用查询字段加索引

# 预加载关系
from sqlalchemy.orm import joinedload

stocks = db.query(Stock).options(joinedload(Stock.category)).all()
```

## 练习题

1. 实现用户的 CRUD API（包含分页、筛选、排序）
2. 实现「收藏」功能：用户可以收藏股票（多对多关系）
3. 实现「软删除」功能，删除的记录可以恢复
4. 实现「乐观锁」更新，防止并发冲突
5. 实现「批量操作」API（批量创建、更新、删除）
