"""复权因子 ORM 模型"""

from datetime import date
from sqlalchemy import String, Float, Date, Integer, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class BaseAdjFactorDB(Base, TimestampMixin):
    """复权因子

    物理表名: base_adj_factors
    UK: (symbol, trade_date)
    """

    __tablename__ = "base_adj_factors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    adj_factor: Mapped[float] = mapped_column(Float, nullable=False, comment="复权因子")

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", name="uq_base_adj_factors_uk"),
        Index("ix_base_adj_factors_date", "trade_date"),
    )

    def __repr__(self) -> str:
        return f"<BaseAdjFactorDB {self.symbol} {self.trade_date}>"
