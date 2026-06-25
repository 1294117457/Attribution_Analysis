"""K线数据模型"""

from sqlalchemy import Column, Integer, String, Float, Date, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class KLine(Base):
    """K线表 - 存储股票日K线数据"""

    __tablename__ = "klines"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 股票信息
    code: Mapped[str] = mapped_column(String(10), nullable=False, index=True, comment="股票代码")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="股票名称")

    # 日期
    date: Mapped[Date] = mapped_column(Date, nullable=False, index=True, comment="交易日期")

    # 价格数据
    open: Mapped[float] = mapped_column(Float, nullable=False, comment="开盘价")
    high: Mapped[float] = mapped_column(Float, nullable=False, comment="最高价")
    low: Mapped[float] = mapped_column(Float, nullable=False, comment="最低价")
    close: Mapped[float] = mapped_column(Float, nullable=False, comment="收盘价")

    # 量价数据
    volume: Mapped[float] = mapped_column(Float, nullable=False, comment="成交量(手)")
    amount: Mapped[float] = mapped_column(Float, nullable=False, comment="成交额(元)")

    # 衍生数据
    change_pct: Mapped[float | None] = mapped_column(Float, nullable=True, comment="涨跌幅(%)")
    turnover_rate: Mapped[float | None] = mapped_column(Float, nullable=True, comment="换手率(%)")

    # 联合唯一索引
    __table_args__ = (
        Index("idx_code_date", "code", "date", unique=True),
        Index("idx_code_date_desc", "code", date.desc()),
    )

    def __repr__(self) -> str:
        return f"<KLine(code={self.code}, name={self.name}, date={self.date}, close={self.close})>"
