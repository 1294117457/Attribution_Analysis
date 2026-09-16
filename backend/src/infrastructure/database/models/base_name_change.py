"""股票曾用名 ORM 模型"""

from datetime import date
from sqlalchemy import String, Integer, Date, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class BaseNameChangeDB(Base, TimestampMixin):
    """股票曾用名

    物理表名: base_name_changes
    UK: (symbol, start_date)
    """

    __tablename__ = "base_name_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    ann_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    change_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("symbol", "start_date", name="uq_base_name_change_uk"),
        Index("ix_base_name_change_symbol", "symbol"),
    )

    def __repr__(self) -> str:
        return f"<BaseNameChangeDB {self.symbol} {self.start_date} {self.name}>"
