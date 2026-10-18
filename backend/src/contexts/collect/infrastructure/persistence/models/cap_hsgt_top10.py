"""沪深港通前10持仓 ORM 模型"""

from datetime import date
from sqlalchemy import String, Float, Date, Index, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.orm_base import RawBase
from shared.infrastructure.persistence.mixins import TimestampMixin


class CapHsgtTop10DB(RawBase, TimestampMixin):
    """沪深港通前10持仓

    物理表名: capital_hsgt_top10
    UK: (trade_date, symbol)
    数据来源: Tushare hsgt_top10
    """

    __tablename__ = "capital_hsgt_top10"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    # 持股信息
    holding_days: Mapped[int | None] = mapped_column(Integer, nullable=True)        # 持股天数
    share_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)        # 持股占总股本比
    hold_amount: Mapped[float | None] = mapped_column(Float, nullable=True)        # 持仓市值（元）
    net_amount: Mapped[float | None] = mapped_column(Float, nullable=True)        # 净买入额

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("trade_date", "symbol", name="uq_cap_hsgt_top10_date_symbol"),
        Index("ix_cap_hsgt_top10_trade_date", "trade_date"),
    )

    def __repr__(self) -> str:
        return f"<CapHsgtTop10DB {self.trade_date} {self.symbol}>"


__all__ = ["CapHsgtTop10DB"]
