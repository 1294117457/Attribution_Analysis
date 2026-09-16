"""板块行情 ORM 模型（行业/概念）"""

from datetime import date
from sqlalchemy import String, Float, Date, Index, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class MktSectorDailyDB(Base, TimestampMixin):
    """板块行情

    物理表名: mkt_sector_dailys
    UK: (sector_type, sector_code, trade_date)
    """

    __tablename__ = "mkt_sector_dailys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    sector_type: Mapped[str] = mapped_column(String(16), nullable=False, comment="板块类型: industry/concept/area")
    sector_code: Mapped[str] = mapped_column(String(32), nullable=False, comment="板块代码")
    sector_name: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="板块名称")
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)

    close: Mapped[float | None] = mapped_column(Float, nullable=True)
    open: Mapped[float | None] = mapped_column(Float, nullable=True)
    high: Mapped[float | None] = mapped_column(Float, nullable=True)
    low: Mapped[float | None] = mapped_column(Float, nullable=True)
    pre_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    change: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    vol: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    turnover_rate: Mapped[float | None] = mapped_column(Float, nullable=True)

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("sector_type", "sector_code", "trade_date", name="uq_mkt_sector_dailys_uk"),
        Index("ix_mkt_sector_dailys_type_date", "sector_type", "trade_date"),
        Index("ix_mkt_sector_dailys_code", "sector_code"),
    )

    def __repr__(self) -> str:
        return f"<MktSectorDailyDB {self.sector_code} {self.trade_date}>"
