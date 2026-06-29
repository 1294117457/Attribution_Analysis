"""股票数据模型"""

from sqlalchemy import Column, String, Float, Integer, Date, Index
from app.database.base import Base
from app.database.models.base import TimestampMixin


class StockKlineDB(Base, TimestampMixin):
    """K 线数据 ORM 模型"""

    __tablename__ = "stock_klines"

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
    change_pct = Column(Float, nullable=True)  # 涨跌幅 %

    # 复合唯一索引
    __table_args__ = (Index("idx_symbol_date", "symbol", "date", unique=True),)

    def __repr__(self):
        return f"<StockKlineDB {self.symbol} {self.date} close={self.close}>"
