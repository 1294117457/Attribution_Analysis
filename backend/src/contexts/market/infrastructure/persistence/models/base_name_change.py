"""股票曾用名 ORM 模型

表名：tech_namechange（对齐 Tushare 接口名 pro.namechange）
UK: (symbol, start_date)
"""

from datetime import date
from sqlalchemy import String, Integer, Date, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.orm_base import RawBase
from shared.infrastructure.persistence.mixins import TimestampMixin


class BaseNameChangeDB(RawBase, TimestampMixin):
    """股票曾用名

    UK: (symbol, start_date)
    """

    __tablename__ = "tech_namechange"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    ann_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    change_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("symbol", "start_date", name="uq_tech_namechange_uk"),
    )

    def __repr__(self) -> str:
        return f"<BaseNameChangeDB {self.symbol} {self.start_date} {self.name}>"
