"""日频估值指标 ORM 模型"""

from datetime import date
from sqlalchemy import String, Float, Date, Index, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class FinDailyBasicDB(Base, TimestampMixin):
    """日频估值指标（PE/PB/PS/换手率等）

    物理表名: fin_daily_basics
    UK: (symbol, trade_date)
    """

    __tablename__ = "fin_daily_basics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)

    close: Mapped[float | None] = mapped_column(Float, nullable=True)
    turnover_rate: Mapped[float | None] = mapped_column(Float, nullable=True, comment="换手率%")
    turnover_rate_f: Mapped[float | None] = mapped_column(Float, nullable=True, comment="换手率(自由流通)")
    volume_ratio: Mapped[float | None] = mapped_column(Float, nullable=True, comment="量比")
    pe: Mapped[float | None] = mapped_column(Float, nullable=True, comment="市盈率(动)")
    pe_ttm: Mapped[float | None] = mapped_column(Float, nullable=True, comment="市盈率TTM")
    pb: Mapped[float | None] = mapped_column(Float, nullable=True, comment="市净率")
    ps: Mapped[float | None] = mapped_column(Float, nullable=True, comment="市销率")
    ps_ttm: Mapped[float | None] = mapped_column(Float, nullable=True, comment="市销率TTM")
    dv_ratio: Mapped[float | None] = mapped_column(Float, nullable=True, comment="股息率%")
    dv_ttm: Mapped[float | None] = mapped_column(Float, nullable=True, comment="股息率TTM%")
    total_share: Mapped[float | None] = mapped_column(Float, nullable=True, comment="总股本(万股)")
    float_share: Mapped[float | None] = mapped_column(Float, nullable=True, comment="流通股本(万股)")
    free_share: Mapped[float | None] = mapped_column(Float, nullable=True, comment="自由流通股本(万股)")
    total_mv: Mapped[float | None] = mapped_column(Float, nullable=True, comment="总市值(万元)")
    circ_mv: Mapped[float | None] = mapped_column(Float, nullable=True, comment="流通市值(万元)")

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", name="uq_fin_daily_basics_uk"),
        Index("ix_fin_daily_basics_date", "trade_date"),
    )

    def __repr__(self) -> str:
        return f"<FinDailyBasicDB {self.symbol} {self.trade_date}>"
