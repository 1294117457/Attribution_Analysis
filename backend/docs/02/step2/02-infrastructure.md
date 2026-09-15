# 02 - Infrastructure 基础设施层

> 基础设施层负责技术细节实现：数据库连接、ORM 模型、仓储实现、防腐层（采集器）。
> 基础设施层**实现领域层定义的接口**，不包含业务逻辑。

---

## 目录结构

```
src/infrastructure/
├── __init__.py
├── config.py                     # 配置管理（pydantic-settings）
│
├── database/                     # 数据库基础设施
│   ├── __init__.py
│   ├── base.py                  # DeclarativeBase
│   ├── connection.py            # 异步引擎、Session
│   ├── mixins.py                # TimestampMixin
│   └── models/                  # ORM 模型（PO）
│       ├── __init__.py
│       ├── kline.py             # DailyKlineDB
│       └── stock_info.py        # StockInfoDB
│
├── repositories/                 # 仓储实现
│   ├── __init__.py
│   ├── kline_repository.py      # KlineRepoImpl
│   └── stock_repository.py       # StockRepoImpl
│
└── collectors/                   # ACL 防腐层（数据采集）
    ├── __init__.py
    ├── interfaces.py             # FetcherProtocol
    ├── base.py                   # Collector 基类
    └── akshare/
        ├── __init__.py
        ├── fetcher.py            # AkShareFetcher
        └── parser.py             # KlineParser
```

---

## infrastructure/config.py 配置管理

```python
"""应用配置（基于 pydantic-settings）"""

import threading
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""
    
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    # ── 服务 ──────────────────────────────────────────────
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    DEBUG: bool = False
    
    # ── PostgreSQL ────────────────────────────────────────
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/stock_db"
    
    # 连接池
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    
    # ── CORS ──────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # ── 数据源（Phase 2）──────────────────────────────────
    TUSHARE_TOKEN: str = ""
    
    # ── API 版本 ──────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"


# 线程安全单例
_settings: Settings | None = None
_lock = threading.Lock()


@lru_cache
def get_settings() -> Settings:
    """获取配置单例（线程安全）"""
    global _settings
    if _settings is None:
        with _lock:
            if _settings is None:
                _settings = Settings()
    return _settings
```

**.env 示例：**

```ini
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/stock_db
DEBUG=false
PORT=8000
TUSHARE_TOKEN=your_token_here
ALLOWED_ORIGINS=["http://localhost:3000"]
```

---

## database/ 数据库基础设施

### database/base.py 声明基类

```python
"""SQLAlchemy 声明基类"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有 ORM 模型的基类"""
    pass
```

### database/mixins.py 混入类

```python
"""ORM 模型混入类"""

from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """自动管理 created_at / updated_at"""
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

### database/connection.py 异步连接管理

```python
"""PostgreSQL 数据库连接（异步）"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from infrastructure.config import get_settings

settings = get_settings()


def _to_async_url(url: str) -> str:
    """postgresql:// → postgresql+asyncpg://"""
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


# 异步引擎
async_engine = create_async_engine(
    _to_async_url(settings.DATABASE_URL),
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=1800,
    connect_args={
        "timeout": 5,
        "command_timeout": 30,
        "statement_cache_size": 0,
    },
)

# Session 工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Depends 注入用
    
    用法：
        @router.get("/")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Service 层独立事务用（非 Depends 场景）
    
    用法：
        async with get_db_context() as db:
            await kline_repo.save_batch(db, klines)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close_db() -> None:
    """关闭连接池（lifespan cleanup 调用）"""
    await async_engine.dispose()
```

### database/models/ ORM 模型

#### models/kline.py

```python
"""日K线 ORM 模型（PO - Persistent Object）"""

from datetime import date, datetime
from sqlalchemy import String, Float, Integer, Date, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class DailyKlineDB(Base, TimestampMixin):
    """日K线数据库模型
    
    表：daily_klines
    唯一约束：(symbol, date)
    """
    
    __tablename__ = "daily_klines"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_kline_symbol_date"),
        Index("ix_kline_symbol_date", "symbol", "date"),
    )
    
    def __repr__(self) -> str:
        return f"<DailyKlineDB {self.symbol} {self.date} close={self.close}>"
```

#### models/stock_info.py

```python
"""股票信息 ORM 模型"""

from datetime import date
from sqlalchemy import String, Integer, Date, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class StockInfoDB(Base, TimestampMixin):
    """股票信息数据库模型
    
    表：stock_infos
    唯一约束：symbol
    """
    
    __tablename__ = "stock_infos"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    market: Mapped[str | None] = mapped_column(String(50), nullable=True)
    list_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_shares: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    
    def __repr__(self) -> str:
        return f"<StockInfoDB {self.symbol} {self.name}>"
```

---

## repositories/ 仓储实现

### repositories/kline_repository.py

```python
"""K线仓储实现"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import select, delete, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.kline.entity import Kline
from domain.kline.value_objects import StockCode
from domain.kline.repository import KlineRepository
from infrastructure.database.models.kline import DailyKlineDB


class KlineRepoImpl:
    """K线仓储实现
    
    实现 domain.kline.repository.KlineRepository 接口。
    负责 ORM 与领域实体之间的转换。
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    # ── ORM → Entity 转换 ────────────────────────────────────
    
    def _to_entity(self, row: DailyKlineDB) -> Kline:
        """ORM 行 → 领域实体"""
        return Kline.from_data(
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
    
    # ── Entity → ORM 转换 ────────────────────────────────────
    
    @staticmethod
    def _to_row(kline: Kline) -> dict:
        """领域实体 → ORM 行字典"""
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
    
    # ── KlineRepository 接口实现 ─────────────────────────────
    
    async def save(self, kline: Kline) -> Kline:
        """保存单条K线"""
        row = DailyKlineDB(**self._to_row(kline))
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return self._to_entity(row)
    
    async def save_batch(self, klines: list[Kline]) -> int:
        """批量保存K线，返回实际新增条数"""
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
    
    async def find_by_id(self, id: int) -> Optional[Kline]:
        """根据ID查询"""
        stmt = select(DailyKlineDB).where(DailyKlineDB.id == id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None
    
    async def find_by_symbol_date(
        self, 
        symbol: StockCode, 
        trade_date: date
    ) -> Optional[Kline]:
        """根据股票代码和日期查询"""
        stmt = select(DailyKlineDB).where(
            DailyKlineDB.symbol == symbol.code,
            DailyKlineDB.date == trade_date,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None
    
    async def find_by_symbol(
        self,
        symbol: StockCode,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 365,
        order_desc: bool = True,
    ):
        """根据股票代码查询K线列表"""
        from domain.kline.entity import KlineCollection
        
        stmt = select(DailyKlineDB).where(DailyKlineDB.symbol == symbol.code)
        
        if start_date:
            stmt = stmt.where(DailyKlineDB.date >= start_date)
        if end_date:
            stmt = stmt.where(DailyKlineDB.date <= end_date)
        
        order_col = DailyKlineDB.date.desc() if order_desc else DailyKlineDB.date.asc()
        stmt = stmt.order_by(order_col).limit(limit)
        
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        
        collection = KlineCollection(symbol=symbol)
        for row in rows:
            collection.add(self._to_entity(row))
        
        return collection
    
    async def count_by_symbol(self, symbol: StockCode) -> int:
        """统计K线条数"""
        stmt = select(func.count()).where(DailyKlineDB.symbol == symbol.code)
        result = await self._session.execute(stmt)
        return result.scalar_one()
    
    async def delete_by_symbol(self, symbol: StockCode) -> int:
        """删除某股票所有K线"""
        stmt = delete(DailyKlineDB).where(DailyKlineDB.symbol == symbol.code)
        result = await self._session.execute(stmt)
        return result.rowcount
    
    async def delete_one(self, symbol: StockCode, trade_date: date) -> int:
        """删除单条K线"""
        stmt = delete(DailyKlineDB).where(
            DailyKlineDB.symbol == symbol.code,
            DailyKlineDB.date == trade_date,
        )
        result = await self._session.execute(stmt)
        return result.rowcount
    
    async def exists(self, symbol: StockCode, trade_date: date) -> bool:
        """检查K线是否存在"""
        stmt = select(
            select(DailyKlineDB.id).where(
                DailyKlineDB.symbol == symbol.code,
                DailyKlineDB.date == trade_date,
            ).exists()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()


# 实现 KlineRepository 接口
KlineRepoImpl.__implements__ = KlineRepository
```

### repositories/stock_repository.py

```python
"""股票信息仓储实现"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.stock_info.entity import StockInfo
from domain.stock_info.value_objects import StockCode
from domain.stock_info.repository import StockInfoRepository
from infrastructure.database.models.stock_info import StockInfoDB
from infrastructure.database.models.kline import DailyKlineDB


class StockRepoImpl:
    """股票信息仓储实现"""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    def _to_entity(self, row: StockInfoDB) -> StockInfo:
        """ORM → Entity"""
        return StockInfo.create(
            id=row.id,
            symbol=row.symbol,
            name=row.name or "",
            industry=row.industry,
            market=row.market,
            list_date=row.list_date,
            total_shares=row.total_shares,
        )
    
    @staticmethod
    def _to_row(stock: StockInfo) -> dict:
        """Entity → ORM"""
        return {
            "symbol": stock.symbol.code,
            "name": stock.name,
            "industry": stock.industry.name if stock.industry else None,
            "market": stock.market.code if stock.market else None,
            "list_date": stock.list_date,
            "total_shares": stock.total_shares,
        }
    
    async def save(self, stock: StockInfo) -> StockInfo:
        """保存股票信息"""
        row = StockInfoDB(**self._to_row(stock))
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return self._to_entity(row)
    
    async def find_by_symbol(self, symbol: StockCode) -> Optional[StockInfo]:
        """根据股票代码查询"""
        stmt = select(StockInfoDB).where(StockInfoDB.symbol == symbol.code)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None
    
    async def find_all(self) -> list[StockInfo]:
        """查询所有股票"""
        stmt = select(StockInfoDB).order_by(StockInfoDB.symbol)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_entity(row) for row in rows]
    
    async def upsert(self, stock: StockInfo) -> StockInfo:
        """插入或更新"""
        stmt = (
            pg_insert(StockInfoDB)
            .values(**self._to_row(stock))
            .on_conflict_do_update(
                index_elements=["symbol"],
                set_=self._to_row(stock),
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return stock
    
    async def delete(self, symbol: StockCode) -> bool:
        """删除股票"""
        stmt = select(StockInfoDB).where(StockInfoDB.symbol == symbol.code)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row:
            await self._session.delete(row)
            return True
        return False
    
    async def list_with_kline_stats(self) -> list[dict]:
        """查询所有股票（含K线统计）"""
        stmt = (
            select(
                StockInfoDB.symbol,
                StockInfoDB.name,
                StockInfoDB.industry,
                StockInfoDB.market,
                func.count(DailyKlineDB.id).label("record_count"),
                func.min(DailyKlineDB.date).label("kline_start"),
                func.max(DailyKlineDB.date).label("kline_end"),
            )
            .outerjoin(DailyKlineDB, StockInfoDB.symbol == DailyKlineDB.symbol)
            .group_by(StockInfoDB.id)
            .order_by(StockInfoDB.symbol)
        )
        result = await self._session.execute(stmt)
        rows = result.all()
        return [row._asdict() for row in rows]


# 实现接口
StockRepoImpl.__implements__ = StockInfoRepository
```

---

## repositories/__init__.py

```python
"""仓储实现导出"""

from infrastructure.repositories.kline_repository import KlineRepoImpl
from infrastructure.repositories.stock_repository import StockRepoImpl

__all__ = ["KlineRepoImpl", "StockRepoImpl"]
```

---

## database/__init__.py

```python
"""数据库基础设施导出"""

from infrastructure.database.base import Base
from infrastructure.database.connection import (
    get_db,
    get_db_context,
    close_db,
    async_engine,
    AsyncSessionLocal,
)
from infrastructure.database.mixins import TimestampMixin
from infrastructure.database.models.kline import DailyKlineDB
from infrastructure.database.models.stock_info import StockInfoDB

__all__ = [
    "Base",
    "get_db",
    "get_db_context",
    "close_db",
    "async_engine",
    "AsyncSessionLocal",
    "TimestampMixin",
    "DailyKlineDB",
    "StockInfoDB",
]
```

---

## 注意事项

1. **PO 与 Domain 分离**：ORM 模型（`DailyKlineDB`）是数据持久化对象，领域实体（`Kline`）是业务对象，两者是不同概念
2. **仓储实现依赖注入**：仓储实现类不直接持有 `AsyncSession`，而是通过构造函数注入，便于测试
3. **批量操作性能**：使用 PostgreSQL 的 `on_conflict_do_nothing` 实现去重插入，避免先查后插的性能问题
4. **ORM 转换在仓储层**：领域实体和 ORM 对象之间的转换统一在仓储层处理，保持领域层纯净
5. **会话管理**：
   - API 层使用 `Depends(get_db)` 自动管理提交/回滚
   - Service 层使用 `get_db_context()` 手动管理事务
