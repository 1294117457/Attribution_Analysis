"""停复牌 ORM 模型"""

from datetime import date
from sqlalchemy import String, Date, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class BaseSuspendDB(Base, TimestampMixin):
    """停复牌

    物理表名: base_suspends
    """

    __tablename__ = "base_suspends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    suspend_timing: Mapped[date | None] = mapped_column(Date, nullable=True)
    suspend_type: Mapped[str | None] = mapped_column(String(8), nullable=True, comment="S=停牌/R=复牌")

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        Index("ix_base_suspends_symbol_date", "symbol", "trade_date"),
        Index("ix_base_suspends_date", "trade_date"),
    )

    def __repr__(self) -> str:
        return f"<BaseSuspendDB {self.symbol} {self.trade_date} {self.suspend_type}>"
