"""龙虎榜每日 ORM 模型"""

from datetime import date
from sqlalchemy import String, Float, Date, Index, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class CapTopListDB(Base, TimestampMixin):
    """龙虎榜每日统计

    物理表名: cap_top_lists
    UK: (trade_date, symbol, reason)
    """

    __tablename__ = "cap_top_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)

    close: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    turnover_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)

    l_sell: Mapped[float | None] = mapped_column(Float, nullable=True, comment="龙虎榜卖出额")
    l_buy: Mapped[float | None] = mapped_column(Float, nullable=True, comment="龙虎榜买入额")
    l_amount: Mapped[float | None] = mapped_column(Float, nullable=True, comment="龙虎榜成交额")
    net_amount: Mapped[float | None] = mapped_column(Float, nullable=True, comment="净买入额")
    net_rate: Mapped[float | None] = mapped_column(Float, nullable=True, comment="净买/总成交")
    amount_rate: Mapped[float | None] = mapped_column(Float, nullable=True, comment="成交额占比")
    float_values: Mapped[float | None] = mapped_column(Float, nullable=True, comment="流通市值")

    reason: Mapped[str | None] = mapped_column(String(256), nullable=True, comment="上榜原因")

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("trade_date", "symbol", "reason", name="uq_cap_top_lists_uk"),
        Index("ix_cap_top_lists_date", "trade_date"),
        Index("ix_cap_top_lists_symbol", "symbol"),
    )

    def __repr__(self) -> str:
        return f"<CapTopListDB {self.symbol} {self.trade_date}>"
