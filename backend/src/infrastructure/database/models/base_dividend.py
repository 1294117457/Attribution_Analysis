"""分红送股 ORM 模型"""

from datetime import date
from sqlalchemy import String, Float, Date, Integer, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class BaseDividendDB(Base, TimestampMixin):
    """分红送股

    物理表名: base_dividends
    UK: (symbol, end_date, div_proc)
    """

    __tablename__ = "base_dividends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    ann_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    record_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    ex_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    pay_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    div_proc: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="实施进度")
    stk_div: Mapped[float | None] = mapped_column(Float, nullable=True, comment="每股送股")
    stk_bo_rate: Mapped[float | None] = mapped_column(Float, nullable=True, comment="每股转增比例")
    stk_co_rate: Mapped[float | None] = mapped_column(Float, nullable=True, comment="每股送股比例")
    cash_div: Mapped[float | None] = mapped_column(Float, nullable=True, comment="每股派息(税前)")
    cash_div_tax: Mapped[float | None] = mapped_column(Float, nullable=True, comment="每股派息(税后)")

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("symbol", "end_date", "div_proc", name="uq_base_dividends_uk"),
        Index("ix_base_dividends_date", "end_date"),
    )

    def __repr__(self) -> str:
        return f"<BaseDividendDB {self.symbol} {self.end_date}>"
