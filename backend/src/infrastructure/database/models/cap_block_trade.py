"""大宗交易 ORM 模型"""

from datetime import date
from sqlalchemy import String, Float, Date, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class CapBlockTradeDB(Base, TimestampMixin):
    """大宗交易

    物理表名: cap_block_trades
    """

    __tablename__ = "cap_block_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)

    price: Mapped[float | None] = mapped_column(Float, nullable=True, comment="成交价")
    vol: Mapped[float | None] = mapped_column(Float, nullable=True, comment="成交量(万股)")
    amount: Mapped[float | None] = mapped_column(Float, nullable=True, comment="成交金额")

    buyer: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="买方营业部")
    seller: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="卖方营业部")

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        Index("ix_cap_block_trades_symbol_date", "symbol", "trade_date"),
        Index("ix_cap_block_trades_date", "trade_date"),
    )

    def __repr__(self) -> str:
        return f"<CapBlockTradeDB {self.symbol} {self.trade_date}>"
