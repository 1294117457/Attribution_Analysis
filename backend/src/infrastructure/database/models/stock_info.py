"""股票信息 ORM 模型"""

from datetime import date
from sqlalchemy import String, Integer, Date, BigInteger, Index
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class StockInfoDB(Base, TimestampMixin):
    """股票信息数据库模型（PO）

    字段对齐 Tushare stock_basic：
    - ts_code / symbol / name
    - area / industry / market
    - exchange (SSE/SZSE/BSE)
    - list_date / delist_date
    - list_status (L/D/P)
    - is_hs (N/H/S)
    """

    __tablename__ = "stock_infos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 主标识
    symbol: Mapped[str] = mapped_column(
        String(10), unique=True, nullable=False, index=True,
        comment="股票代码（6位）",
    )
    ts_code: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True,
        comment="Tushare 统一代码（含交易所后缀）",
    )
    name: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # 业务字段
    area: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True,
        comment="地域",
    )
    industry: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True,
        comment="行业",
    )
    market: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True,
        comment="市场类型（主板/科创板/创业板/北交所）",
    )
    exchange: Mapped[str | None] = mapped_column(
        String(10), nullable=True, index=True,
        comment="交易所代码 SSE/SZSE/BSE",
    )

    # 时间字段
    list_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    delist_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    list_status: Mapped[str | None] = mapped_column(
        String(5), nullable=True, default="L", index=True,
        comment="上市状态 L/D/P",
    )

    # 沪深港通 + 股本
    is_hs: Mapped[str | None] = mapped_column(
        String(5), nullable=True, default="N",
        comment="沪深港通 N/H/S",
    )
    total_shares: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # 实控人信息
    act_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
        comment="实控人名称",
    )
    act_ent_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="实控人企业性质",
    )

    __table_args__ = (
        Index("ix_stock_industry_market", "industry", "market"),
        Index("ix_stock_exchange_status", "exchange", "list_status"),
    )

    def __repr__(self) -> str:
        return f"<StockInfoDB {self.symbol} {self.name}>"
