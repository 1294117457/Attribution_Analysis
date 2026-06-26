"""
ORM 模型，描述数据库表结构。
用于 SQLAlchemy ORM 查询（db.query() 风格）。
建表用 scripts/init_db.py 执行 SQL，不依赖这些模型。
"""

from sqlalchemy import Column, Integer, String, Float, Date, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class KLine(Base):
    __tablename__ = "klines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    date = Column(Date, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    change_pct = Column(Float)
    turnover_rate = Column(Float)

    __table_args__ = (
        Index("idx_code_date", "code", "date", unique=True),
    )
