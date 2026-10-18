"""沪深港通资金流向 ORM 模型（北向资金）"""

from datetime import date
from sqlalchemy import String, Float, Date, Index, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.orm_base import RawBase
from shared.infrastructure.persistence.mixins import TimestampMixin


class CapMoneyflowHsgtDB(RawBase, TimestampMixin):
    """沪深港通资金流向（北向资金）

    物理表名: capital_moneyflow_hsgt
    UK: (trade_date, exchange)
    数据来源: Tushare moneyflow_hsgt
    """

    __tablename__ = "capital_moneyflow_hsgt"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    exchange: Mapped[str] = mapped_column(String(8), nullable=False)  # SH/SZ/HK

    # 买入/卖出/净买入
    buy_amount: Mapped[float | None] = mapped_column(Float, nullable=True)   # 买入额（元）
    sell_amount: Mapped[float | None] = mapped_column(Float, nullable=True)  # 卖出额（元）
    net_amount: Mapped[float | None] = mapped_column(Float, nullable=True)   # 净买入额

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("trade_date", "exchange", name="uq_cap_moneyflow_hsgt_date_exchange"),
        Index("ix_cap_moneyflow_hsgt_trade_date", "trade_date"),
    )

    def __repr__(self) -> str:
        return f"<CapMoneyflowHsgtDB {self.trade_date} {self.exchange}>"


__all__ = ["CapMoneyflowHsgtDB"]
