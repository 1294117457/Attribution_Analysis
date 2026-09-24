# 03 - model + repo 数据持久层

> **model.py**：SQLAlchemy ORM 映射，只定义数据库表结构，无业务逻辑。
> **repo.py**：数据访问层，只做 SQL 读写，无业务规则，全部使用 AsyncSession。

---

## kline 域

### kline/model.py

```python
"""日K线 ORM 模型（PO - Persistent Object）"""

from datetime import date, datetime
from sqlalchemy import String, Float, Integer, Date, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from infra.database.base import Base
from infra.database.mixins import TimestampMixin


class DailyKlineDB(Base, TimestampMixin):
    """日K线数据库模型

    表：daily_klines
    唯一约束：(symbol, date) → 避免重复采集
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

### kline/repo.py

```python
"""K线数据访问层（只做 SQL，无业务规则）"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import select, delete, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from kline.model import DailyKlineDB
from kline.schema import DailyKlineData


class KlineRepo:
    """DailyKlineDB 的数据访问层"""

    # ── 读 ──────────────────────────────────────────────────

    @staticmethod
    async def get_by_symbol_date(
        db: AsyncSession, symbol: str, trade_date: date
    ) -> Optional[DailyKlineDB]:
        stmt = select(DailyKlineDB).where(
            DailyKlineDB.symbol == symbol,
            DailyKlineDB.date == trade_date,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def query(
        db: AsyncSession,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 365,
        order_asc: bool = True,
    ) -> list[DailyKlineDB]:
        """按 symbol + 日期范围查询 K 线，用于 API 返回和指标计算"""
        stmt = select(DailyKlineDB).where(DailyKlineDB.symbol == symbol)

        if start_date:
            stmt = stmt.where(DailyKlineDB.date >= start_date)
        if end_date:
            stmt = stmt.where(DailyKlineDB.date <= end_date)

        order_col = DailyKlineDB.date.asc() if order_asc else DailyKlineDB.date.desc()
        stmt = stmt.order_by(order_col).limit(limit)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def count_by_symbol(db: AsyncSession, symbol: str) -> int:
        stmt = select(func.count()).where(DailyKlineDB.symbol == symbol)
        result = await db.execute(stmt)
        return result.scalar_one()

    @staticmethod
    async def get_date_range(
        db: AsyncSession, symbol: str
    ) -> tuple[Optional[date], Optional[date]]:
        """获取某 symbol 的最早和最新日期"""
        stmt = select(
            func.min(DailyKlineDB.date),
            func.max(DailyKlineDB.date),
        ).where(DailyKlineDB.symbol == symbol)
        result = await db.execute(stmt)
        row = result.one()
        return row[0], row[1]

    # ── 写 ──────────────────────────────────────────────────

    @staticmethod
    async def save_batch(
        db: AsyncSession, klines: list[DailyKlineData]
    ) -> int:
        """批量插入，遇到 (symbol, date) 冲突则跳过（on conflict do nothing）。
        返回实际插入条数。
        """
        if not klines:
            return 0

        rows = [
            {
                "symbol": k.symbol,
                "name": k.name,
                "date": k.trade_date,
                "open": k.open,
                "high": k.high,
                "low": k.low,
                "close": k.close,
                "volume": k.volume,
                "amount": k.amount,
                "change_pct": k.change_pct,
            }
            for k in klines
        ]

        stmt = (
            pg_insert(DailyKlineDB)
            .values(rows)
            .on_conflict_do_nothing(constraint="uq_kline_symbol_date")
        )
        result = await db.execute(stmt)
        return result.rowcount

    # ── 删 ──────────────────────────────────────────────────

    @staticmethod
    async def delete_by_symbol(db: AsyncSession, symbol: str) -> int:
        stmt = delete(DailyKlineDB).where(DailyKlineDB.symbol == symbol)
        result = await db.execute(stmt)
        return result.rowcount

    @staticmethod
    async def delete_one(db: AsyncSession, symbol: str, trade_date: date) -> int:
        stmt = delete(DailyKlineDB).where(
            DailyKlineDB.symbol == symbol,
            DailyKlineDB.date == trade_date,
        )
        result = await db.execute(stmt)
        return result.rowcount
```

---

## stock_info 域

### stock_info/model.py

```python
"""股票基本信息 ORM 模型"""

from datetime import date
from sqlalchemy import String, Integer, Date, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from infra.database.base import Base
from infra.database.mixins import TimestampMixin


class StockInfoDB(Base, TimestampMixin):
    """股票基本信息

    表：stock_infos
    唯一约束：symbol（一只股票只有一条记录）
    """

    __tablename__ = "stock_infos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    market: Mapped[str | None] = mapped_column(String(50), nullable=True)   # 沪市/深市/北交所
    list_date: Mapped[date | None] = mapped_column(Date, nullable=True)      # 上市日期
    total_shares: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # 总股本（万股）

    def __repr__(self) -> str:
        return f"<StockInfoDB {self.symbol} {self.name}>"
```

### stock_info/repo.py

```python
"""股票信息数据访问层"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from stock_info.model import StockInfoDB
from kline.model import DailyKlineDB  # 用于 list_with_kline_stats 联合查询


class StockInfoRepo:

    # ── 读 ──────────────────────────────────────────────────

    @staticmethod
    async def get_by_symbol(
        db: AsyncSession, symbol: str
    ) -> Optional[StockInfoDB]:
        stmt = select(StockInfoDB).where(StockInfoDB.symbol == symbol)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_with_kline_stats(db: AsyncSession) -> list[dict]:
        """返回所有股票列表 + K线条数 + 日期范围（首页列表用）"""
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
        result = await db.execute(stmt)
        rows = result.all()
        return [row._asdict() for row in rows]

    # ── 写 ──────────────────────────────────────────────────

    @staticmethod
    async def upsert(
        db: AsyncSession,
        symbol: str,
        name: str,
        industry: Optional[str] = None,
        market: Optional[str] = None,
    ) -> None:
        """插入或更新股票信息（on conflict update name）"""
        stmt = (
            pg_insert(StockInfoDB)
            .values(symbol=symbol, name=name, industry=industry, market=market)
            .on_conflict_do_update(
                index_elements=["symbol"],
                set_={"name": name, "industry": industry, "market": market},
            )
        )
        await db.execute(stmt)
```

---

## 注意事项

1. **使用 `pg_insert` 的 `on_conflict_do_nothing`**：比先查后插性能好，避免 N+1 问题
2. **`save_batch` 一次性批量插入**：不要循环单条 insert，性能差 100 倍以上
3. **Repo 方法都是 `@staticmethod`**：参考 ID 项目，传入 `db` 而不是存在实例上，方便测试和复用
4. **`list_with_kline_stats` 联合查询**：`stock_info/repo.py` 需要 import `kline/model.py`，这是 repo 层唯一允许的跨域 import（只 import model，不 import service）
5. **`mapped_column` 类型注解**：使用 SQLAlchemy 2.0 风格的 `Mapped[type]`，支持 IDE 类型推断

---

## 数据库初始化

model 写好后，在 `app/main.py` 的 lifespan 中建表：

```python
# app/main.py lifespan
from infra.database.base import Base
from infra.database.connection import async_engine

# 需要 import 所有 model，确保 metadata 注册
import kline.model       # noqa: F401
import stock_info.model  # noqa: F401

async with async_engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
```
