"""日 K 线 ORM 模型（仅 OHLCV，技术指标请求时实时计算）

表名重命名：tech_kline_daily → tech_daily
类名：TechKlineDailyDB（保持不变，避免业务/仓储层大改）
"""

from datetime import date
from sqlalchemy import String, Float, Integer, Date, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.orm_base import RawBase
from shared.infrastructure.persistence.mixins import TimestampMixin


class TechKlineDailyDB(RawBase, TimestampMixin):
    """日K线数据库模型（PO）

    一行 = (symbol, date) → 当日 OHLCV。
    """

    __tablename__ = "tech_daily"

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
        UniqueConstraint("symbol", "date", name="uq_tech_daily_symbol_date"),
        Index("ix_tech_daily_symbol_date", "symbol", "date"),
    )

    def __repr__(self) -> str:
        return f"<TechKlineDailyDB {self.symbol} {self.date} close={self.close}>"
