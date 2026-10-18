"""每日涨停板 ORM 模型"""

from datetime import date, time
from sqlalchemy import String, Float, Date, Time, Index, UniqueConstraint, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.orm_base import RawBase
from shared.infrastructure.persistence.mixins import TimestampMixin


class MarketLimitListDB(RawBase, TimestampMixin):
    """每日涨停板

    物理表名: market_limit_list
    UK: (trade_date, symbol)
    数据来源: Tushare limit_list_d
    """

    __tablename__ = "market_limit_list"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # 行情
    close_price: Mapped[float | None] = mapped_column(Float, nullable=True)       # 收盘价
    change_rate: Mapped[float | None] = mapped_column(Float, nullable=True)        # 涨跌幅（%）

    # 涨停属性
    limit_type: Mapped[str | None] = mapped_column(String(8), nullable=True)      # up_limit / down_limit
    board_count: Mapped[int | None] = mapped_column(Integer, nullable=True)       # 连板数
    first_limit_time: Mapped[time | None] = mapped_column(Time, nullable=True)     # 首次涨停时间
    board_strength: Mapped[float | None] = mapped_column(Float, nullable=True)     # 封板强度

    # 涨停原因
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("trade_date", "symbol", name="uq_market_limit_list_date_symbol"),
        Index("ix_market_limit_list_trade_date", "trade_date"),
        Index("ix_market_limit_list_board_count", "board_count"),
    )

    def __repr__(self) -> str:
        return f"<MarketLimitListDB {self.trade_date} {self.symbol} {self.name}>"


__all__ = ["MarketLimitListDB"]
