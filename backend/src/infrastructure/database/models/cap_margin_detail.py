"""个股两融明细 ORM 模型"""

from datetime import date
from sqlalchemy import String, Float, Date, Index, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class CapMarginDetailDB(Base, TimestampMixin):
    """个股两融明细

    物理表名: cap_margin_details
    UK: (symbol, trade_date)
    """

    __tablename__ = "cap_margin_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)

    rzye: Mapped[float | None] = mapped_column(Float, nullable=True, comment="融资余额")
    rqye: Mapped[float | None] = mapped_column(Float, nullable=True, comment="融券余额")
    rzmre: Mapped[float | None] = mapped_column(Float, nullable=True, comment="融资买入额")
    rqyl: Mapped[float | None] = mapped_column(Float, nullable=True, comment="融券余量")
    rzche: Mapped[float | None] = mapped_column(Float, nullable=True, comment="融资偿还额")
    rqchl: Mapped[float | None] = mapped_column(Float, nullable=True, comment="融券偿还量")
    rqmcl: Mapped[float | None] = mapped_column(Float, nullable=True, comment="融券卖出量")
    rzrqye: Mapped[float | None] = mapped_column(Float, nullable=True, comment="融资融券余额")

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", name="uq_cap_margin_details_uk"),
        Index("ix_cap_margin_details_date", "trade_date"),
    )

    def __repr__(self) -> str:
        return f"<CapMarginDetailDB {self.symbol} {self.trade_date}>"
