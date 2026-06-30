"""股票信息 ORM 模型"""

from sqlalchemy import Column, String, Integer, DateTime
from infra.database.base import Base
from infra.database.models.mixins import TimestampMixin


class StockInfoDB(Base, TimestampMixin):
    """股票信息数据库模型"""

    __tablename__ = "stock_infos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=True)
    industry = Column(String(100), nullable=True)
    market = Column(String(50), nullable=True)
    list_date = Column(String(20), nullable=True)
    total_shares = Column(String(50), nullable=True)

    def __repr__(self):
        return f"<StockInfoDB {self.symbol} {self.name}>"
