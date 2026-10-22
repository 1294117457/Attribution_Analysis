"""停复牌 ORM 模型

表名：tech_suspend_d（对齐 Tushare 接口名 pro.suspend_d）
"""

from datetime import date
from sqlalchemy import String, Date, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.orm_base import RawBase
from shared.infrastructure.persistence.mixins import TimestampMixin


class BaseSuspendDB(RawBase, TimestampMixin):
    """停复牌（Tushare pro.suspend_d）"""

    __tablename__ = "tech_suspend_d"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Tushare 文档 suspend_timing 类型为 str（"09:30-10:00"），存为 varchar
    suspend_timing: Mapped[str | None] = mapped_column(String(32), nullable=True)
    suspend_type: Mapped[str | None] = mapped_column(String(8), nullable=True, comment="S=停牌/R=复牌")

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        Index("ix_tech_suspend_d_symbol_date", "symbol", "trade_date"),
        Index("ix_tech_suspend_d_date", "trade_date"),
    )

    def __repr__(self) -> str:
        return f"<BaseSuspendDB {self.symbol} {self.trade_date} {self.suspend_type}>"