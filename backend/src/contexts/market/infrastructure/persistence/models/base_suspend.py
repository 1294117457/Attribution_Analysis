"""停复牌 ORM 模型"""

from datetime import date
from sqlalchemy import String, Date, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.orm_base import RawBase
from shared.infrastructure.persistence.mixins import TimestampMixin


class BaseSuspendDB(RawBase, TimestampMixin):
    """停复牌

    物理表名: base_suspends
    """

    __tablename__ = "tech_suspend"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Tushare 文档 suspend_timing 类型为 str（"09:30-10:00"），存为 varchar
    suspend_timing: Mapped[str | None] = mapped_column(String(32), nullable=True)
    suspend_type: Mapped[str | None] = mapped_column(String(8), nullable=True, comment="S=停牌/R=复牌")

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        Index("ix_base_suspends_symbol_date", "symbol", "trade_date"),
        Index("ix_base_suspends_date", "trade_date"),
    )

    def __repr__(self) -> str:
        return f"<BaseSuspendDB {self.symbol} {self.trade_date} {self.suspend_type}>"
