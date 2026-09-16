"""个股资金流向 ORM 模型"""

from datetime import date
from sqlalchemy import String, Float, Date, Index, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class CapMoneyflowDB(Base, TimestampMixin):
    """个股资金流向

    物理表名: cap_moneyflows
    UK: (symbol, trade_date)
    """

    __tablename__ = "cap_moneyflows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)

    # 小单
    buy_sm_vol: Mapped[float | None] = mapped_column(Float, nullable=True)
    buy_sm_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_sm_vol: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_sm_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 中单
    buy_md_vol: Mapped[float | None] = mapped_column(Float, nullable=True)
    buy_md_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_md_vol: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_md_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 大单
    buy_lg_vol: Mapped[float | None] = mapped_column(Float, nullable=True)
    buy_lg_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_lg_vol: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_lg_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 特大单
    buy_elg_vol: Mapped[float | None] = mapped_column(Float, nullable=True)
    buy_elg_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_elg_vol: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_elg_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 净流入
    net_mf_vol: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_mf_amount: Mapped[float | None] = mapped_column(Float, nullable=True)

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", name="uq_cap_moneyflow_symbol_date"),
        Index("ix_cap_moneyflow_date", "trade_date"),
    )

    def __repr__(self) -> str:
        return f"<CapMoneyflowDB {self.symbol} {self.trade_date}>"
