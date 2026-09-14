# 01 - infra 基础设施层

> 职责：提供数据库连接、配置读取等基础能力，无任何业务逻辑。
> 所有其他层都可以依赖 infra，但 infra 不依赖任何业务域。

---

## 目录结构

```
src/infra/
├── __init__.py
├── config.py               ← 环境变量读取（pydantic-settings）
└── database/
    ├── __init__.py
    ├── base.py             ← declarative_base()
    ├── connection.py       ← 异步引擎 + get_db() + get_db_context()
    └── mixins.py           ← TimestampMixin
```

---

## infra/config.py

```python
"""环境配置（pydantic-settings）"""

import threading
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── 服务 ──────────────────────────────────────
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    DEBUG: bool = False

    # ── PostgreSQL ─────────────────────────────────
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/stock_db"

    # 连接池（参考 ID 项目）
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # ── CORS ───────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ── Tushare（Phase 2 使用）─────────────────────
    TUSHARE_TOKEN: str = ""

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


# 线程安全单例
_settings: Settings | None = None
_lock = threading.Lock()


def get_settings() -> Settings:
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
TUSHARE_TOKEN=your_token_here
ALLOWED_ORIGINS=["http://localhost:3000"]
```

---

## infra/database/base.py

```python
"""SQLAlchemy 声明基类"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

---

## infra/database/mixins.py

```python
"""ORM 公共字段 Mixin"""

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

---

## infra/database/connection.py

**关键改动：同步 Session → 异步 AsyncSession**

```python
"""PostgreSQL 数据库连接（异步）"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from infra.config import get_settings

settings = get_settings()


def _to_async_url(url: str) -> str:
    """postgresql:// → postgresql+asyncpg://（幂等）"""
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


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

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Depends 注入用。
    正常结束自动 commit，异常自动 rollback。
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
    """Service 内部独立事务用（非 Depends 场景）。
    
    用法：
        async with get_db_context() as db:
            await KlineRepo.save_batch(db, klines)
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

---

## infra/database/__init__.py

```python
from .base import Base
from .connection import get_db, get_db_context, close_db, async_engine
from .mixins import TimestampMixin

__all__ = [
    "Base", "get_db", "get_db_context", "close_db",
    "async_engine", "TimestampMixin",
]
```

---

## 注意事项

1. **asyncpg 驱动**：需要安装 `asyncpg`（`pip install asyncpg`），不再使用 `psycopg2`
2. **所有 repo/service 函数必须是 `async def`**，否则 `await db.execute()` 无法使用
3. **`expire_on_commit=False`**：异步场景下 commit 后访问属性不会触发 lazy load 报错
4. **`statement_cache_size=0`**：兼容 PgBouncer 连接池代理，生产环境推荐保留

---

## 依赖安装

```bash
pip install sqlalchemy asyncpg pydantic-settings
```
