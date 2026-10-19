"""沪深股通十大成交股 ORM 模型（Tushare hsgt_top10 接口全字段）

接口: Tushare pro.hsgt_top10
物理表名: capital_hsgt_top10
UK: (trade_date, market_type, symbol, rank)
"""

from datetime import date
from sqlalchemy import String, Float, Date, Index, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.orm_base import RawBase
from shared.infrastructure.persistence.mixins import TimestampMixin


class CapitalHsgtTop10DB(RawBase, TimestampMixin):
    """沪深股通十大成交股（Tushare hsgt_top10 接口）

    一行 = (trade_date, market_type, rank) 当日某市场北向资金 top10 之一。
    """

    __tablename__ = "capital_hsgt_top10"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    market_type: Mapped[str] = mapped_column(String(8), nullable=False, comment="1=沪市/3=深市")
    rank: Mapped[int] = mapped_column(Integer, nullable=False, comment="资金排名 1~10")

    # 行情
    close: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_change: Mapped[float | None] = mapped_column(Float, nullable=True, comment="涨跌额(元) — 文档字段 change")

    # 资金
    amount: Mapped[float | None] = mapped_column(Float, nullable=True, comment="成交金额(元)")
    net_amount: Mapped[float | None] = mapped_column(Float, nullable=True, comment="净成交金额(元)")
    buy: Mapped[float | None] = mapped_column(Float, nullable=True, comment="买入金额(元)")
    sell: Mapped[float | None] = mapped_column(Float, nullable=True, comment="卖出金额(元)")

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint(
            "trade_date", "market_type", "symbol", "rank",
            name="uq_capital_hsgt_top10_uk",
        ),
        Index("ix_capital_hsgt_top10_trade_date", "trade_date"),
        Index("ix_capital_hsgt_top10_symbol", "symbol"),
        Index("ix_capital_hsgt_top10_market_date", "market_type", "trade_date"),
    )

    def __repr__(self) -> str:
        return f"<CapitalHsgtTop10DB {self.trade_date} mkt={self.market_type} rank={self.rank} {self.symbol}>"


__all__ = ["CapitalHsgtTop10DB"]
