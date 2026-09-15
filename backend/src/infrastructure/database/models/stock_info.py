"""股票信息 ORM 模型"""

from datetime import date
from sqlalchemy import String, Integer, Date, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class StockInfoDB(Base, TimestampMixin):
    """股票信息数据库模型（PO）"""

    __tablename__ = "stock_infos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    market: Mapped[str | None] = mapped_column(String(50), nullable=True)
    list_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_shares: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    def __repr__(self) -> str:
        return f"<StockInfoDB {self.symbol} {self.name}>"
