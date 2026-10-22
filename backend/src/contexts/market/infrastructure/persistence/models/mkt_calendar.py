"""交易日历 ORM 模型

表名：tech_trade_cal（对齐 Tushare 接口名 pro.trade_cal）
UK: (cal_date, exchange)
"""

from datetime import date
from sqlalchemy import String, Integer, Date, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.orm_base import RawBase
from shared.infrastructure.persistence.mixins import TimestampMixin


class MktCalendarDB(RawBase, TimestampMixin):
    """交易日历（Tushare pro.trade_cal）

    UK: (cal_date, exchange)
    """

    __tablename__ = "tech_trade_cal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    exchange: Mapped[str] = mapped_column(String(16), nullable=False)
    cal_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_open: Mapped[bool] = mapped_column(nullable=False, default=True)
    pretrade_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("cal_date", "exchange", name="uq_tech_trade_cal_uk"),
        Index("ix_tech_trade_cal_exchange_date", "exchange", "cal_date"),
    )

    def __repr__(self) -> str:
        return f"<MktCalendarDB {self.exchange} {self.cal_date} open={self.is_open}>"