"""两融汇总 ORM 模型"""

from datetime import date
from sqlalchemy import String, Float, Date, Index, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class CapMarginDB(Base, TimestampMixin):
    """两融汇总（按交易所）

    物理表名: cap_margins
    UK: (exchange_id, trade_date)
    """

    __tablename__ = "cap_margins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    exchange_id: Mapped[str] = mapped_column(String(16), nullable=False, comment="交易所代码 SSE/SZSE")

    rzye: Mapped[float | None] = mapped_column(Float, nullable=True, comment="融资余额(元)")
    rzmre: Mapped[float | None] = mapped_column(Float, nullable=True, comment="融资买入额(元)")
    rzche: Mapped[float | None] = mapped_column(Float, nullable=True, comment="融资偿还额(元)")
    rqye: Mapped[float | None] = mapped_column(Float, nullable=True, comment="融券余额(元)")
    rqmcl: Mapped[float | None] = mapped_column(Float, nullable=True, comment="融券卖出量(股)")
    rzrqye: Mapped[float | None] = mapped_column(Float, nullable=True, comment="融资融券余额(元)")
    rqyl: Mapped[float | None] = mapped_column(Float, nullable=True, comment="融券余量(股)")

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("exchange_id", "trade_date", name="uq_cap_margins_uk"),
        Index("ix_cap_margins_date", "trade_date"),
    )

    def __repr__(self) -> str:
        return f"<CapMarginDB {self.exchange_id} {self.trade_date}>"
