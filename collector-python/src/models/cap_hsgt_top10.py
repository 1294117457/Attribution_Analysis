"""沪深港通前10成交 ORM 模型"""

from datetime import date
from sqlalchemy import String, Float, Date, Index, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from core.db import RawBase
from core.db import TimestampMixin


class CapHsgtTop10DB(RawBase, TimestampMixin):
    """沪深股通每日十大成交股

    物理表名: capital_hsgt_top10
    UK: (trade_date, market_type, symbol, rank)
    数据来源: Tushare hsgt_top10

    ★ 结构 = Tushare 官方接口列（2025-10-29 实测核对）：
      trade_date, ts_code, name, close, change, rank, market_type,
      amount, net_amount, buy, sell
    ❌ 原 ORM 的 holding_days / share_ratio / hold_amount 是自造字段，
       上游**根本不提供** → 已删除。
    """

    __tablename__ = "capital_hsgt_top10"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)

    market_type: Mapped[str] = mapped_column(String(8), nullable=False)   # 1=沪市 3=深市
    rank: Mapped[int] = mapped_column(Integer, nullable=False)             # 资金排名 1-10

    close: Mapped[float | None] = mapped_column(Float, nullable=True)      # 收盘价
    change: Mapped[float | None] = mapped_column(Float, nullable=True)     # 涨跌额
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)     # 成交金额（元）

    net_amount: Mapped[float | None] = mapped_column(Float, nullable=True)  # 净成交金额（元）
    buy: Mapped[float | None] = mapped_column(Float, nullable=True)         # 买入金额（元）
    sell: Mapped[float | None] = mapped_column(Float, nullable=True)        # 卖出金额（元）

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("trade_date", "market_type", "symbol", "rank",
                         name="uq_capital_hsgt_top10_uk"),
        Index("ix_capital_hsgt_top10_trade_date", "trade_date"),
        Index("ix_capital_hsgt_top10_symbol", "symbol"),
    )

    def __repr__(self) -> str:
        return f"<CapHsgtTop10DB {self.trade_date} {self.symbol} rank={self.rank}>"


__all__ = ["CapHsgtTop10DB"]
