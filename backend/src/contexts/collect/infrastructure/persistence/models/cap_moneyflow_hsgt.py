"""沪深港通资金流向 ORM 模型（北向资金，按 Tushare 文档全字段）

接口: Tushare pro.moneyflow_hsgt
物理表名: capital_moneyflow_hsgt
UK: (trade_date, symbol, market_type)
"""

from datetime import date
from sqlalchemy import String, Float, Date, Index, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.orm_base import RawBase
from shared.infrastructure.persistence.mixins import TimestampMixin


class CapitalMoneyflowHsgtDB(RawBase, TimestampMixin):
    """沪深港通资金流向（按股票粒度，对应 Tushare moneyflow_hsgt 接口）

    一行 = (trade_date, symbol, market_type) 单只股票当日的北向资金情况。
    """

    __tablename__ = "capital_moneyflow_hsgt"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # 1=沪市 / 3=深市 / 2=港股
    market_type: Mapped[str] = mapped_column(String(8), nullable=False)

    # 行情
    close: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_change: Mapped[float | None] = mapped_column(Float, nullable=True, comment="涨跌额(元) — 文档字段 change")
    pct_change: Mapped[float | None] = mapped_column(Float, nullable=True, comment="涨跌幅(%)")
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="资金排名")

    # 资金
    amount: Mapped[float | None] = mapped_column(Float, nullable=True, comment="成交金额(元)")
    net_amount: Mapped[float | None] = mapped_column(Float, nullable=True, comment="净成交金额(元)")
    buy: Mapped[float | None] = mapped_column(Float, nullable=True, comment="买入金额(元)")
    sell: Mapped[float | None] = mapped_column(Float, nullable=True, comment="卖出金额(元)")

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint(
            "trade_date", "symbol", "market_type",
            name="uq_capital_moneyflow_hsgt_uk",
        ),
        Index("ix_capital_moneyflow_hsgt_trade_date", "trade_date"),
        Index("ix_capital_moneyflow_hsgt_symbol", "symbol"),
        Index("ix_capital_moneyflow_hsgt_symbol_date", "symbol", "trade_date"),
    )

    def __repr__(self) -> str:
        return f"<CapitalMoneyflowHsgtDB {self.trade_date} {self.symbol} mkt={self.market_type}>"


__all__ = ["CapitalMoneyflowHsgtDB"]
