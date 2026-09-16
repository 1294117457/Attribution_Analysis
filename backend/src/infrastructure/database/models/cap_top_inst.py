"""龙虎榜机构席位 ORM 模型"""

from datetime import date
from sqlalchemy import String, Float, Date, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class CapTopInstDB(Base, TimestampMixin):
    """龙虎榜机构席位明细

    物理表名: cap_top_insts
    UK: 主键 id 即可
    """

    __tablename__ = "cap_top_insts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    exalter: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="营业部名称")
    side: Mapped[str | None] = mapped_column(String(8), nullable=True, comment="买卖方向: 0=卖/1=买")

    buy: Mapped[float | None] = mapped_column(Float, nullable=True, comment="买入额")
    buy_rate: Mapped[float | None] = mapped_column(Float, nullable=True, comment="买入占总成交比")
    sell: Mapped[float | None] = mapped_column(Float, nullable=True, comment="卖出额")
    sell_rate: Mapped[float | None] = mapped_column(Float, nullable=True, comment="卖出占总成交比")
    net_buy: Mapped[float | None] = mapped_column(Float, nullable=True, comment="净额")

    reason: Mapped[str | None] = mapped_column(String(256), nullable=True, comment="上榜原因")

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        Index("ix_cap_top_insts_symbol_date", "symbol", "trade_date"),
        Index("ix_cap_top_insts_date", "trade_date"),
    )

    def __repr__(self) -> str:
        return f"<CapTopInstDB {self.symbol} {self.trade_date} {self.side}>"
