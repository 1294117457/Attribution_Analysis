# App 模块设计分析

## 1. 模块定位

```
┌─────────────────────────────────────────────────────────────────┐
│                        外部请求 (HTTP)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          app/ (API 层)                          │
│                                                                 │
│   api/ ──────────▶ API 路由定义                                  │
│   models/ ───────▶ 请求/响应 DTO                                │
│   database/ ─────▶ ORM 模型 + 连接管理                            │
│   services/ ─────▶ 业务逻辑                                      │
│   main.py ───────▶ FastAPI 入口                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       data/ml/rag/graph                          │
└─────────────────────────────────────────────────────────────────┘
```

## 2. 分层职责

| 层级 | 目录 | 职责 | 特点 |
|------|------|------|------|
| 接口层 | `api/` | 路由、参数校验、响应格式化 | 轻量，无业务逻辑 |
| DTO 层 | `models/` | Pydantic 请求/响应模型 | 与 API 强相关 |
| 服务层 | `services/` | 业务逻辑、领域转换 | 可复用 |
| ORM 层 | `database/models/` | SQLAlchemy 模型 | 与数据库强相关 |

## 3. 数据流向

```
HTTP 请求
    │
    ▼
api/anomalies.py (路由)
    │
    ▼
models/anomaly.py (AnomalyCreate - 请求验证)
    │
    ▼
services/anomaly_service.py (业务逻辑)
    │
    ├──▶ database/models/anomaly_db.py (写入 DB)
    │
    ▼
models/anomaly.py (AnomalyResponse - 响应格式化)
    │
    ▼
HTTP 响应
```

## 4. API 设计原则

### 4.1 RESTful 风格

| 操作 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 创建 | POST | `/anomalies` | 创建异常 |
| 查询 | GET | `/anomalies/{id}` | 获取单个 |
| 列表 | GET | `/anomalies/stock/{symbol}` | 按股票查询 |
| 更新 | PUT | `/anomalies/{id}` | 更新异常 |
| 删除 | DELETE | `/anomalies/{id}` | 删除异常 |

### 4.2 响应格式

```python
class AnomalyListResponse(BaseModel):
    total: int           # 总数
    items: list[...]     # 列表项

class ErrorResponse(BaseModel):
    detail: str          # 错误详情
```

### 4.3 状态码

| 状态码 | 使用场景 |
|--------|----------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 5. ORM 设计

### 5.1 Base 类设计

```python
class Base(DeclarativeBase):
    """SQLAlchemy 基础类"""
    pass

class TimestampMixin:
    """时间戳混入"""
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**设计理由**：
- `Base` 使用 `DeclarativeBase` (SQLAlchemy 2.0)
- `TimestampMixin` 自动记录创建和更新时间

### 5.2 ORM 与 Pydantic 转换

```python
# ORM → Pydantic
class AnomalyResponse(BaseModel):
    class Config:
        from_attributes = True  # 关键配置

# 使用
orm_obj = db.query(AnomalyDB).first()
response = AnomalyResponse.model_validate(orm_obj)
```

### 5.3 索引设计

```python
class StockKlineDB(Base):
    __table_args__ = (
        Index("idx_symbol_date", "symbol", "date", unique=True),
    )
```

**索引策略**：
- 主键自动索引
- 外键建立索引
- 频繁查询的字段建立索引
- 唯一约束自动索引

## 6. 服务层设计

### 6.1 服务类结构

```python
class AnomalyService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: AnomalyCreate) -> AnomalyResponse:
        ...

    def list_by_symbol(...) -> list[AnomalyResponse]:
        ...

    def to_record(self, response: AnomalyResponse) -> AnomalyRecord:
        """转换为 core 领域模型"""
        ...
```

### 6.2 领域模型转换

```
app/models/anomaly.py (DTO)
        │
        │  AnomalyResponse.model_validate()
        ▼
app/database/models/anomaly_db.py (ORM)
        │
        │  AnomalyService.to_record()
        ▼
core/models/anomaly.py (领域模型)
```

**设计理由**：
- 层级之间解耦
- core 不依赖 app
- 便于测试和替换

## 7. 依赖注入设计

### 7.1 FastAPI 依赖注入

```python
# dependencies.py
def get_anomaly_service(db: Session = Depends(get_db)) -> AnomalyService:
    return AnomalyService(db)

# api/anomalies.py
@router.post("")
def create_anomaly(
    data: AnomalyCreate,
    service: AnomalyService = Depends(get_anomaly_service),
):
    return service.create(data)
```

### 7.2 依赖注入链

```
get_db ──────────────▶ SessionLocal
    │                      │
    ▼                      ▼
get_anomaly_service ──── AnomalyService(db)
    │
    ▼
API 路由使用 service
```

## 8. 配置管理

```python
# app/config.py
from core.config import get_settings

settings = get_settings()

# 使用
DATABASE_URL = settings.DATABASE_URL
```

**设计理由**：
- 复用 core 的配置
- app 不直接读取 .env

## 9. 错误处理

```python
from fastapi import HTTPException

@router.get("/{symbol}")
def get_stock(symbol: str, db: Session = Depends(get_db)):
    stock = service.get_by_symbol(symbol)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    return stock
```

## 10. 扩展指南

### 10.1 添加新的 API

1. `app/models/` - 定义 DTO
2. `app/database/models/` - 定义 ORM (如需要)
3. `app/services/` - 定义服务类
4. `app/api/` - 定义路由
5. `app/api/router.py` - 注册路由

### 10.2 添加新的数据库表

1. `app/database/models/` - 创建 ORM 类
2. `app/api/main.py` - `on_startup` 会自动创建

### 10.3 数据库迁移 (推荐使用 Alembic)

```bash
alembic init alembic
alembic revision --autogenerate -m "create stock_klines"
alembic upgrade head
```

## 11. 测试策略

```python
# tests/test_app/test_anomalies.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_anomaly():
    response = client.post("/api/v1/anomalies", json={...})
    assert response.status_code == 201
    assert response.json()["symbol"] == "000001"

def test_list_anomalies():
    response = client.get("/api/v1/anomalies/stock/000001")
    assert response.status_code == 200
    assert "items" in response.json()
```
