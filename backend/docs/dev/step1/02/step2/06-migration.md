# 06 - Migration 迁移指南

> 从 Phase 1 架构**彻底重构**到 Phase 2 DDD 架构的完整指南。
> **不考虑向后兼容**，直接替换整个后端结构。
> 推荐在新仓库或新分支执行，可以大幅减少历史包袱。

---

## 迁移概览

### Phase 1 现状（待重构）

```
backend/
├── app/
│   ├── main.py
│   ├── dependencies.py
│   ├── api/v1/stocks.py
│   └── schemas/stock.py
├── data/
│   ├── services/stock_service.py    # 混合了 K线和股票的业务逻辑
│   ├── collectors/collector.py
│   ├── adapters/akshare/fetcher.py
│   ├── interfaces/fetcher.py
│   ├── parsers/kline_parser.py
│   └── schemas/kline.py
├── infra/
│   ├── config.py
│   └── database/
│       ├── base.py
│       ├── connection.py
│       └── models/
│           ├── stock.py
│           └── stock_info.py
└── test_*.py
```

### Phase 2 目标（DDD 架构）

```
backend/src/
├── main.py                          # FastAPI 应用入口
├── dependencies.py                  # 项目级依赖
│
├── domain/                          # ⭐ 领域层（DDD 核心）
│   ├── base.py
│   ├── events.py
│   ├── kline/
│   │   ├── entity.py
│   │   ├── value_objects.py
│   │   ├── schemas.py
│   │   ├── events.py
│   │   └── repository.py
│   └── stock_info/
│       ├── entity.py
│       ├── value_objects.py
│       ├── schemas.py
│       └── repository.py
│
├── application/                     # ⭐ 应用层
│   ├── kline_service.py
│   ├── stock_service.py
│   ├── exceptions.py
│   └── dto/
│       ├── kline.py
│       └── stock.py
│
├── infrastructure/                  # ⭐ 基础设施层
│   ├── config.py
│   ├── database/
│   │   ├── base.py
│   │   ├── connection.py
│   │   ├── mixins.py
│   │   └── models/
│   │       ├── kline.py
│   │       └── stock_info.py
│   ├── repositories/
│   │   ├── kline_repository.py
│   │   └── stock_repository.py
│   └── collectors/
│       ├── interfaces.py
│       ├── base.py
│       └── akshare/
│           ├── fetcher.py
│           └── parser.py
│
└── route/                            # ⭐ 路由层（原 interfaces）
    ├── api/
    │   ├── v1/
    │   │   ├── kline.py
    │   │   └── stock.py
    │   └── router.py
    ├── schemas/
    │   └── response.py
    └── dependencies.py
```

---

## 完整重构步骤

### Step 1: 清理旧目录

首先**彻底删除** Phase 1 的旧代码：

```bash
cd backend/

# 删除旧的 app 目录（除 main.py 模板外）
rm -rf app/api/
rm -rf app/schemas/
rm -rf app/dependencies.py

# 删除整个 data 目录
rm -rf data/

# 重命名 infra 为 src/infrastructure（可选，也可重写结构）
# 推荐直接删除并重建
rm -rf infra/

# 创建新的 src 目录结构
mkdir -p src/domain/kline
mkdir -p src/domain/stock_info
mkdir -p src/application/dto
mkdir -p src/infrastructure/database/models
mkdir -p src/infrastructure/repositories
mkdir -p src/infrastructure/collectors/akshare
mkdir -p src/route/api/v1
mkdir -p src/route/schemas
mkdir -p tests/
```

**说明**：
- 不保留任何旧文件，所有代码按照 DDD 架构重新组织
- 旧的 `app/`、`data/`、`infra/` 全部删除
- 创建清晰的 `src/` 目录结构

---

### Step 2: 创建领域层（自底向上第一步）

领域层不依赖任何外部框架，**必须先完成**。

#### 2.1 创建 `domain/base.py`

```python
"""领域层基类"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime


@dataclass
class Entity(ABC):
    """实体基类"""
    @property
    @abstractmethod
    def id(self) -> Any: ...
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        return hash(self.id)


@dataclass
class AggregateRoot(Entity, ABC):
    """聚合根基类"""
    _domain_events: list = field(default_factory=list, init=False, repr=False)
    
    def add_event(self, event) -> None:
        self._domain_events.append(event)
    
    def clear_events(self) -> list:
        events = self._domain_events.copy()
        self._domain_events.clear()
        return events
    
    @property
    def domain_events(self) -> list:
        return self._domain_events.copy()


@dataclass(frozen=True)
class ValueObject(ABC):
    """值对象基类"""
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return False
        return self._get_values() == other._get_values()
    
    def __hash__(self) -> int:
        return hash(self._get_values())
    
    @abstractmethod
    def _get_values(self) -> tuple: ...


@dataclass
class DomainEvent:
    """领域事件基类"""
    occurred_on: datetime = field(default_factory=datetime.now)
    
    @property
    def event_type(self) -> str:
        return type(self).__name__
```

#### 2.2 创建 K线聚合 `domain/kline/`

```python
# domain/kline/value_objects.py
from dataclasses import dataclass
from datetime import date
from typing import Optional

from domain.base import ValueObject


@dataclass(frozen=True)
class StockCode(ValueObject):
    """股票代码值对象"""
    code: str
    
    def __post_init__(self):
        if not (self.code and len(self.code) == 6 and self.code.isdigit()):
            raise ValueError(f"无效的股票代码: {self.code}")
    
    def _get_values(self) -> tuple:
        return (self.code,)


@dataclass(frozen=True)
class TradeDate(ValueObject):
    """交易日期值对象"""
    date: date
    
    def _get_values(self) -> tuple:
        return (self.date,)


# domain/kline/entity.py
from dataclasses import dataclass
from datetime import date
from typing import Optional

from domain.base import AggregateRoot
from domain.kline.value_objects import StockCode, TradeDate


@dataclass
class Kline(AggregateRoot):
    """K线聚合根"""
    id: int
    symbol: StockCode
    trade_date: TradeDate
    name: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    change_pct: Optional[float]
    
    @property
    def id(self) -> int:
        return self.id
    
    def validate(self) -> None:
        if self.high < self.low:
            raise ValueError("最高价不能低于最低价")
        if self.high < max(self.open, self.close):
            raise ValueError("最高价异常")
        if self.low > min(self.open, self.close):
            raise ValueError("最低价异常")
    
    @classmethod
    def create(
        cls,
        symbol: str,
        name: str,
        trade_date: date,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        amount: float,
        change_pct: Optional[float] = None,
        id: int = 0,
    ) -> Kline:
        kline = cls(
            id=id,
            symbol=StockCode(symbol),
            trade_date=TradeDate(trade_date),
            name=name,
            open=open,
            high=high,
            low=low,
            close=close,
            volume=volume,
            amount=amount,
            change_pct=change_pct,
        )
        kline.validate()
        return kline
```

```python
# domain/kline/schemas.py
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional


class KlineBO(BaseModel):
    """K线业务对象（采集层产出）"""
    symbol: str
    name: str = ""
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    change_pct: Optional[float] = None
    
    def to_entity(self) -> Kline:
        return Kline.create(
            symbol=self.symbol,
            name=self.name,
            trade_date=self.trade_date,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.volume,
            amount=self.amount,
            change_pct=self.change_pct,
        )


class KlineVO(BaseModel):
    """K线视图对象（API 出参）"""
    symbol: str
    name: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    change_pct: Optional[float] = None
    
    @classmethod
    def from_entity(cls, kline: Kline) -> KlineVO:
        return cls(
            symbol=kline.symbol.code,
            name=kline.name,
            date=kline.trade_date.date,
            open=kline.open,
            high=kline.high,
            low=kline.low,
            close=kline.close,
            volume=kline.volume,
            amount=kline.amount,
            change_pct=kline.change_pct,
        )
```

```python
# domain/kline/repository.py
from datetime import date
from typing import Optional, Protocol

from domain.kline.entity import Kline
from domain.kline.value_objects import StockCode


class KlineRepository(Protocol):
    """K线仓储接口"""
    async def save(self, kline: Kline) -> Kline: ...
    async def save_batch(self, klines: list[Kline]) -> int: ...
    async def find_by_symbol(self, symbol: StockCode, start_date: Optional[date] = None, end_date: Optional[date] = None, limit: int = 365, order_desc: bool = True) -> list[Kline]: ...
    async def find_by_symbol_date(self, symbol: StockCode, trade_date: date) -> Optional[Kline]: ...
    async def count_by_symbol(self, symbol: StockCode) -> int: ...
    async def delete_by_symbol(self, symbol: StockCode) -> int: ...
    async def delete_one(self, symbol: StockCode, trade_date: date) -> int: ...
```

#### 2.3 同样创建 StockInfo 聚合（参见 `01-domain.md` 详细说明）

---

### Step 3: 创建基础设施层

#### 3.1 数据库连接与配置

```python
# infrastructure/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        extra="ignore",
    )
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/stock_db"
    DEBUG: bool = False
    PORT: int = 8000
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

```python
# infrastructure/database/connection.py
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from infrastructure.config import get_settings

settings = get_settings()


def _to_async_url(url: str) -> str:
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


async_engine = create_async_engine(
    _to_async_url(settings.DATABASE_URL),
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=1800,
    connect_args={"timeout": 5, "statement_cache_size": 0},
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close_db() -> None:
    await async_engine.dispose()
```

#### 3.2 ORM 模型

详见 `02-infrastructure.md` 中的代码（这里与原 Phase 1 模型兼容，表结构保持不变）。

#### 3.3 仓储实现

```python
# infrastructure/repositories/kline_repository.py
from sqlalchemy import select, delete, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.kline.entity import Kline
from domain.kline.repository import KlineRepository
from domain.kline.value_objects import StockCode
from infrastructure.database.models.kline import DailyKlineDB


class KlineRepoImpl(KlineRepository):
    """K线仓储实现"""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    def _to_entity(self, row: DailyKlineDB) -> Kline:
        return Kline.create(
            id=row.id,
            symbol=row.symbol,
            name=row.name or "",
            trade_date=row.date,
            open=row.open,
            high=row.high,
            low=row.low,
            close=row.close,
            volume=row.volume,
            amount=row.amount,
            change_pct=row.change_pct,
        )
    
    @staticmethod
    def _to_row(kline: Kline) -> dict:
        return {
            "symbol": kline.symbol.code,
            "name": kline.name,
            "date": kline.trade_date.date,
            "open": kline.open,
            "high": kline.high,
            "low": kline.low,
            "close": kline.close,
            "volume": kline.volume,
            "amount": kline.amount,
            "change_pct": kline.change_pct,
        }
    
    async def save_batch(self, klines: list[Kline]) -> int:
        if not klines:
            return 0
        rows = [self._to_row(k) for k in klines]
        stmt = (
            pg_insert(DailyKlineDB)
            .values(rows)
            .on_conflict_do_nothing(constraint="uq_kline_symbol_date")
        )
        result = await self._session.execute(stmt)
        return result.rowcount
    
    # 实现其他接口方法...
```

---

### Step 4: 创建应用层

```python
# application/exceptions.py
class ApplicationError(Exception):
    """应用层异常基类"""
    def __init__(self, message: str, code: str = "APP_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class KlineNotFoundError(ApplicationError):
    def __init__(self, symbol: str, date: str = None):
        msg = f"股票 {symbol} 在 {date} 的K线不存在" if date else f"股票 {symbol} 的K线不存在"
        super().__init__(msg, "KLINE_NOT_FOUND")


class StockNotFoundError(ApplicationError):
    def __init__(self, symbol: str):
        super().__init__(f"股票 {symbol} 不存在", "STOCK_NOT_FOUND")


class CollectionError(ApplicationError):
    def __init__(self, symbol: str, reason: str):
        super().__init__(f"采集股票 {symbol} 失败: {reason}", "COLLECTION_ERROR")
        self.symbol = symbol
```

```python
# application/kline_service.py
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.kline import KlineCollectRequest, KlineCollectResponse
from application.exceptions import CollectionError
from domain.kline.repository import KlineRepository
from domain.kline.schemas import KlineBO
from infrastructure.collectors.interfaces import CollectParams, FetcherProtocol
from infrastructure.repositories.kline_repository import KlineRepoImpl


class KlineAppService:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo: KlineRepository = KlineRepoImpl(session)
    
    async def collect(
        self,
        request: KlineCollectRequest,
        fetcher: FetcherProtocol,
    ) -> KlineCollectResponse:
        try:
            params = CollectParams(
                symbol=request.symbol,
                days=request.days,
                start_date=request.start_date,
                end_date=request.end_date,
            )
            raw_data = fetcher.fetch(params)
            
            if not raw_data:
                return KlineCollectResponse(
                    symbol=request.symbol,
                    name="",
                    saved_count=0,
                    total_count=0,
                    message="未获取到数据",
                )
            
            klines = [data.to_entity() for data in raw_data]
            name = klines[0].name if klines else ""
            saved_count = await self._repo.save_batch(klines)
            
            return KlineCollectResponse(
                symbol=request.symbol,
                name=name,
                saved_count=saved_count,
                total_count=len(klines),
                message=f"成功采集 {saved_count} 条新数据（共获取 {len(klines)} 条）",
            )
        except Exception as e:
            raise CollectionError(request.symbol, str(e))
```

---

### Step 5: 创建路由层（原 interfaces，已改名 route）

```python
# route/api/v1/kline.py
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from application.kline_service import KlineAppService
from application.dto.kline import KlineCollectRequest, KlineQueryRequest, KlineDeleteRequest
from infrastructure.database.connection import get_db
from infrastructure.collectors.akshare import AkShareFetcher
from domain.kline.schemas import KlineBO
from route.schemas import response as R

router = APIRouter(prefix="/klines", tags=["K线"])


def get_kline_service(db: AsyncSession = Depends(get_db)) -> KlineAppService:
    return KlineAppService(session=db)


@router.post("/collect", status_code=status.HTTP_201_CREATED)
async def collect_kline(
    request: KlineCollectRequest,
    service: KlineAppService = Depends(get_kline_service),
):
    fetcher = AkShareFetcher(KlineBO)
    response = await service.collect(request, fetcher)
    return R.created(response.model_dump())
```

---

### Step 6: 主入口

```python
# main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from infrastructure.config import get_settings
from infrastructure.database.base import Base
from infrastructure.database.connection import async_engine, close_db
from infrastructure.database.models.kline import DailyKlineDB           # noqa
from infrastructure.database.models.stock_info import StockInfoDB        # noqa

from route.api.router import api_router
from application.exceptions import ApplicationError

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await close_db()


app = FastAPI(
    title="智能金融数据归因分析平台",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ApplicationError)
async def app_error(request: Request, exc: ApplicationError):
    return JSONResponse(
        status_code=400,
        content={"code": 400, "message": exc.message, "data": None},
    )


@app.exception_handler(Exception)
async def generic_error(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "服务器内部错误", "data": None},
    )


app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}
```

---

## 代码对照表（彻底替换）

| Phase 1（已删除） | Phase 2（全新） | 说明 |
|------------------|-----------------|------|
| `app/main.py` | `src/main.py` | 完全重写 |
| `app/dependencies.py` | `src/dependencies.py` | 重新组织 |
| `app/api/v1/stocks.py` | `src/route/api/v1/kline.py` + `stock.py` | 拆分并移到 route/ |
| `app/schemas/stock.py` | `src/route/schemas/response.py` + `application/dto/` | 重新组织 |
| `data/services/stock_service.py` | `src/application/kline_service.py` + `stock_service.py` | 拆分 |
| `data/schemas/kline.py` | `src/domain/kline/schemas.py` | 移到领域层 |
| `data/interfaces/fetcher.py` | `src/infrastructure/collectors/interfaces.py` | 改名 |
| `data/collectors/` | `src/infrastructure/collectors/` | 整体移动 |
| `data/adapters/` | `src/infrastructure/collectors/{数据源}/` | 整体移动 |
| `data/parsers/` | `src/infrastructure/collectors/{数据源}/` | 整合 |
| `infra/database/models/stock.py` | `src/infrastructure/database/models/kline.py` | 改名 |
| `infra/database/models/stock_info.py` | `src/infrastructure/database/models/stock_info.py` | 保留但位置变化 |
| `infra/config.py` | `src/infrastructure/config.py` | 移到 src/ |
| `infra/database/connection.py` | `src/infrastructure/database/connection.py` | 移到 src/ |
| `infra/database/base.py` | `src/infrastructure/database/base.py` | 移到 src/ |
| - | `src/domain/` | **新增**：领域层 |
| - | `src/application/dto/` | **新增**：应用 DTO |
| - | `src/infrastructure/repositories/` | **新增**：仓储实现 |

---

## 数据迁移

由于表结构保持兼容（`daily_klines`、`stock_infos` 表名不变），**数据库不需要迁移**。

如果生产环境已经有数据，重构后应用启动时会跳过已存在的表。

---

## API 兼容性

**不考虑向后兼容**，API 端点完全重新设计：

| Phase 1 端点 | Phase 2 端点 | 状态 |
|--------------|--------------|------|
| `POST /api/v1/stocks/collect` | `POST /api/v1/klines/collect` | 重命名 |
| `GET /api/v1/stocks/{symbol}/klines` | `GET /api/v1/klines/{symbol}` | 重构 |
| `DELETE /api/v1/stocks/{symbol}` | `DELETE /api/v1/klines/{symbol}` | 拆分 |

前端需要一并修改。

---

## 测试策略

```python
# tests/test_domain_kline.py - 领域层单元测试（无依赖）
def test_kline_validation_fails_when_high_less_than_low():
    with pytest.raises(ValueError):
        Kline.create(
            symbol="000001",
            name="测试",
            trade_date=date(2024, 1, 1),
            open=10,
            high=8,  # 错误：high < low
            low=10,
            close=9,
            volume=100,
            amount=1000,
        )


# tests/test_application_service.py - 应用层单元测试（mock 依赖）
@pytest.mark.asyncio
async def test_collect_kline_success():
    mock_session = Mock()
    mock_repo = Mock(spec=KlineRepository)
    mock_repo.save_batch.return_value = 100
    mock_fetcher = Mock(spec=FetcherProtocol)
    mock_fetcher.fetch.return_value = [...]
    
    service = KlineAppService(session=mock_session)
    service._repo = mock_repo
    
    request = KlineCollectRequest(symbol="000001", days=365)
    response = await service.collect(request, mock_fetcher)
    
    assert response.saved_count == 100


# tests/test_api_kline.py - API 集成测试（使用 TestClient）
def test_collect_endpoint_returns_201(client):
    response = client.post(
        "/api/v1/klines/collect",
        json={"symbol": "000001", "days": 30},
    )
    assert response.status_code == 201
    assert response.json()["code"] == 201
```

---

## 完整重构检查清单

### Step 1: 环境准备
- [ ] 删除 `app/`、`data/`、`infra/` 整个目录
- [ ] 创建 `src/` 目录结构（domain、application、infrastructure、route）

### Step 2: 领域层（domain/）
- [ ] 实现 `domain/base.py` 基类
- [ ] 实现 `domain/kline/entity.py` 聚合根
- [ ] 实现 `domain/kline/value_objects.py`
- [ ] 实现 `domain/kline/schemas.py`（KlineBO、KlineVO）
- [ ] 实现 `domain/kline/repository.py` 接口
- [ ] 实现 `domain/kline/events.py`
- [ ] 实现 `domain/stock_info/` 同上

### Step 3: 基础设施层（infrastructure/）
- [ ] 实现 `infrastructure/config.py`
- [ ] 实现 `infrastructure/database/connection.py`（注意 asyncpg）
- [ ] 实现 `infrastructure/database/base.py`、`mixins.py`
- [ ] 实现 `infrastructure/database/models/kline.py`
- [ ] 实现 `infrastructure/database/models/stock_info.py`
- [ ] 实现 `infrastructure/repositories/kline_repository.py`
- [ ] 实现 `infrastructure/repositories/stock_repository.py`
- [ ] 实现 `infrastructure/collectors/interfaces.py`
- [ ] 实现 `infrastructure/collectors/base.py`
- [ ] 实现 `infrastructure/collectors/akshare/fetcher.py`
- [ ] 实现 `infrastructure/collectors/akshare/parser.py`

### Step 4: 应用层（application/）
- [ ] 实现 `application/exceptions.py`
- [ ] 实现 `application/dto/kline.py`
- [ ] 实现 `application/dto/stock.py`
- [ ] 实现 `application/kline_service.py`
- [ ] 实现 `application/stock_service.py`

### Step 5: 路由层（route/）
- [ ] 实现 `route/schemas/response.py`
- [ ] 实现 `route/api/v1/kline.py`
- [ ] 实现 `route/api/v1/stock.py`
- [ ] 实现 `route/api/router.py`
- [ ] 实现 `route/dependencies.py`

### Step 6: 应用入口
- [ ] 实现 `src/main.py`
- [ ] 实现 `src/dependencies.py`

### Step 7: 测试与验证
- [ ] 编写领域层单元测试
- [ ] 编写应用层单元测试
- [ ] 编写 API 集成测试
- [ ] 验证 Swagger 文档正常（访问 `/docs`）
- [ ] 验证健康检查接口（`/health`）
- [ ] 验证数据采集功能
- [ ] 验证数据查询功能

### Step 8: 上线
- [ ] 备份生产数据
- [ ] 部署新版本
- [ ] 前端同步更新（API 端点变了）
- [ ] 监控日志

---

## 常见问题

### Q1: 为什么不保留旧代码作为兼容层？

**A**: 保留兼容层会导致：
- 双倍维护成本
- 代码混乱，DDD 价值无法体现
- 长期技术债

推荐一次性切换，在新分支或新仓库完成迁移。Phase 2 的 API 端点更清晰，前端改一次即可。

### Q2: 数据会不会丢？

**A**: 不会。因为：
- ORM 模型保持兼容（表名、列名、约束都不变）
- 重构后启动时 `Base.metadata.create_all` 会跳过已存在的表
- 业务逻辑只是代码组织方式变了，数据持久化方式没变

### Q3: 团队成员如何快速上手？

**A**: 建议：
1. 阅读 `00-index.md` 了解整体架构
2. 重点理解依赖方向：**路由 → 应用 → 领域 → 基础设施**
3. 看到任何 import `infrastructure/` 的代码都应该怀疑是不是放错层了
4. 遇到问题先看现有同类实现，模仿即可

### Q4: 是否需要先写测试再写代码？

**A**: 推荐 TDD，但不是必须。至少要保证：
- 领域实体的业务规则有测试（最高优先级）
- API 集成测试有覆盖（次优先级）
- 仓储实现测试（中优先级）

### Q5: 应用服务和领域服务的区别？

**A**:
- **应用服务**：用例编排（接收 DTO → 调用仓储/采集器 → 返回 DTO），可跨多个聚合
- **领域服务**：业务规则实现（业务逻辑必须放在领域层），通常只在一个聚合内

本项目 Phase 2 主要使用**应用服务**，简单的业务规则直接在领域实体方法中实现（如 `Kline.validate()`）。
