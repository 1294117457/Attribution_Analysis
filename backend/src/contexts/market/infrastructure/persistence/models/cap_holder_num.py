"""股东户数 ORM 模型

表名：capital_stk_holdernumber（对齐 Tushare 接口名 pro.stk_holdernumber）
UK: (symbol, end_date)
"""

from datetime import date
from sqlalchemy import String, Float, Date, Integer, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.orm_base import RawBase
from shared.infrastructure.persistence.mixins import TimestampMixin


class CapHolderNumDB(RawBase, TimestampMixin):
    """股东户数（Tushare pro.stk_holdernumber）

    UK: (symbol, end_date)
    """

    __tablename__ = "capital_stk_holdernumber"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    ann_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    holder_num: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="股东户数")
    holder_nums: Mapped[float | None] = mapped_column(Float, nullable=True, comment="股东户数(详细)")

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("symbol", "end_date", name="uq_capital_stk_holdernumber_uk"),
        Index("ix_capital_stk_holdernumber_date", "end_date"),
    )

    def __repr__(self) -> str:
        return f"<CapHolderNumDB {self.symbol} {self.end_date}>"