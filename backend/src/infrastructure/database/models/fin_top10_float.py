"""前十大流通股东 ORM 模型"""

from datetime import date
from sqlalchemy import String, Float, Date, Integer, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class FinTop10FloatHolderDB(Base, TimestampMixin):
    """前十大流通股东

    物理表名: fin_top10_floatholders
    UK: (symbol, end_date, ann_date, holder_name)
    """

    __tablename__ = "fin_top10_floatholders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    ann_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    holder_name: Mapped[str] = mapped_column(String(128), nullable=False)
    hold_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    hold_ratio: Mapped[float | None] = mapped_column(Float, nullable=True, comment="占流通股本比例%")
    hold_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    holder_type: Mapped[str | None] = mapped_column(String(32), nullable=True)

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint(
            "symbol", "end_date", "ann_date", "holder_name",
            name="uq_fin_top10_floatholders_uk",
        ),
        Index("ix_fin_top10_floatholders_date", "end_date"),
    )

    def __repr__(self) -> str:
        return f"<FinTop10FloatHolderDB {self.symbol} {self.holder_name}>"
