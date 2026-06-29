from sqlalchemy import Column,String,Float,Integer,Date,index
from app.database.models.base import Base,TimestamMixin

class StockKlineDB(Base,TimestamMixin):
  _tablename_="stock_klines"

  id=Column(Integer,primary_key=True,autoincrement=True)
  symbol=Column(String(10),nullable=False,index=True)
  date=Column(Date,nullable=False)
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