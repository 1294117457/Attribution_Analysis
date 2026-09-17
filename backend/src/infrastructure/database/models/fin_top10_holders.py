"""前十大股东 ORM 模型"""

from datetime import date
from sqlalchemy import String, Float, Date, Integer, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class FinTop10HolderDB(Base, TimestampMixin):
    """前十大股东

    物理表名: fin_top10_holders
    UK: (symbol, end_date, ann_date, holder_name)
    """

    __tablename__ = "fin_top10_holders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    ann_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    holder_name: Mapped[str] = mapped_column(String(128), nullable=False)
    hold_amount: Mapped[float | None] = mapped_column(Float, nullable=True, comment="持有数量")
    hold_ratio: Mapped[float | None] = mapped_column(Float, nullable=True, comment="占总股本比例%")
    hold_float_ratio: Mapped[float | None] = mapped_column(Float, nullable=True, comment="占流通股本比例%")
    hold_change: Mapped[float | None] = mapped_column(Float, nullable=True, comment="持股变化")
    holder_type: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="股东类型")

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint(
            "symbol", "end_date", "ann_date", "holder_name",
            name="uq_fin_top10_holders_uk",
        ),
        Index("ix_fin_top10_holders_date", "end_date"),
    )

    def __repr__(self) -> str:
        return f"<FinTop10HolderDB {self.symbol} {self.holder_name}>"
