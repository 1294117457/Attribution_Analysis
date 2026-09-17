"""股东户数 ORM 模型"""

from datetime import date
from sqlalchemy import String, Float, Date, Integer, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class CapHolderNumDB(Base, TimestampMixin):
    """股东户数

    物理表名: cap_holder_nums
    UK: (symbol, end_date)
    """

    __tablename__ = "cap_holder_nums"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    ann_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    holder_num: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="股东户数")
    holder_nums: Mapped[float | None] = mapped_column(Float, nullable=True, comment="股东户数(详细)")

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("symbol", "end_date", name="uq_cap_holder_nums_uk"),
        Index("ix_cap_holder_nums_date", "end_date"),
    )

    def __repr__(self) -> str:
        return f"<CapHolderNumDB {self.symbol} {self.end_date}>"
