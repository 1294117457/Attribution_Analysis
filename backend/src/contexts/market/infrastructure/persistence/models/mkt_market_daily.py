"""指数日行情 ORM 模型

表名：fundamental_index_daily（对齐 Tushare 接口名 pro.index_daily）
UK: (market, trade_date)
"""

from datetime import date
from sqlalchemy import String, Float, Date, Index, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.orm_base import RawBase
from shared.infrastructure.persistence.mixins import TimestampMixin


class MktMarketDailyDB(RawBase, TimestampMixin):
    """指数日行情（Tushare pro.index_daily）

    UK: (market, trade_date)
    """

    __tablename__ = "fundamental_index_daily"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    market: Mapped[str] = mapped_column(String(16), nullable=False, comment="市场代码: SSE/SZSE/CSI")
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)

    close: Mapped[float | None] = mapped_column(Float, nullable=True)
    open: Mapped[float | None] = mapped_column(Float, nullable=True)
    high: Mapped[float | None] = mapped_column(Float, nullable=True)
    low: Mapped[float | None] = mapped_column(Float, nullable=True)
    pre_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    change: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Float, nullable=True)
    vol: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("market", "trade_date", name="uq_fundamental_index_daily_uk"),
        Index("ix_fundamental_index_daily_date", "trade_date"),
    )

    def __repr__(self) -> str:
        return f"<MktMarketDailyDB {self.market} {self.trade_date}>"
