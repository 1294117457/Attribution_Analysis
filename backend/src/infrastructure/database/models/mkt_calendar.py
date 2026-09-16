"""交易日历 ORM 模型"""

from datetime import date
from sqlalchemy import String, Integer, Date, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class MktCalendarDB(Base, TimestampMixin):
    """交易日历

    物理表名: mkt_calendars
    UK: (cal_date, exchange)
    """

    __tablename__ = "mkt_calendars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    exchange: Mapped[str] = mapped_column(String(16), nullable=False)
    cal_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_open: Mapped[bool] = mapped_column(nullable=False, default=True)
    pretrade_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("cal_date", "exchange", name="uq_mkt_calendars_uk"),
        Index("ix_mkt_calendars_exchange_date", "exchange", "cal_date"),
    )

    def __repr__(self) -> str:
        return f"<MktCalendarDB {self.exchange} {self.cal_date} open={self.is_open}>"
