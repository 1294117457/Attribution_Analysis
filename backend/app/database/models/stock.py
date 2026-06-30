"""日K线 ORM 模型"""

from sqlalchemy import Column, String, Float, Integer, Date, Index
from app.database.base import Base
from app.database.models.mixins import TimestampMixin


class DailyKlineDB(Base, TimestampMixin):
    """日K线数据库模型"""

    __tablename__ = "daily_klines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, index=True)
    name = Column(String(50), nullable=True)
    date = Column(Date, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    change_pct = Column(Float, nullable=True)

    __table_args__ = (
        Index("idx_symbol_date", "symbol", "date", unique=True),
    )

    def __repr__(self):
        return f"<DailyKlineDB {self.symbol} {self.date} close={self.close}>"
