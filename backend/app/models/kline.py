from sqlalchemy import Column, Integer, String, Float, Date
from app.models.base import Base


class KLine(Base):
    __tablename__ = "klines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, comment="股票代码")
    name = Column(String(50), nullable=False, comment="股票名称")
    date = Column(Date, nullable=False, comment="交易日期")
    open = Column(Float, nullable=False, comment="开盘价")
    high = Column(Float, nullable=False, comment="最高价")
    low = Column(Float, nullable=False, comment="最低价")
    close = Column(Float, nullable=False, comment="收盘价")
    volume = Column(Float, nullable=False, comment="成交量")
    amount = Column(Float, nullable=False, comment="成交额")
    change_pct = Column(Float, comment="涨跌幅(%)")
    turnover_rate = Column(Float, comment="换手率(%)")
