"""每日涨跌停列表 ORM 模型（Tushare limit_list_d 接口全字段）

接口: Tushare pro.limit_list_d
物理表名: capital_limit_list_d
UK: (trade_date, symbol, limit_type)
"""

from datetime import date
from sqlalchemy import String, Float, Date, Index, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.orm_base import RawBase
from shared.infrastructure.persistence.mixins import TimestampMixin


class CapitalLimitListDDB(RawBase, TimestampMixin):
    """每日涨跌停列表（Tushare limit_list_d 接口）

    一行 = (trade_date, symbol, limit_type) 当日某股票的涨停/跌停记录。
    limit_type: D=跌停 / U=涨停 / Z=炸板
    """

    __tablename__ = "capital_limit_list_d"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    industry: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # 行情
    close: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Float, nullable=True, comment="涨跌幅(%)")

    # 成交/市值
    amount: Mapped[float | None] = mapped_column(Float, nullable=True, comment="成交额(元)")
    limit_amount: Mapped[float | None] = mapped_column(Float, nullable=True, comment="板上成交金额(元)")
    float_mv: Mapped[float | None] = mapped_column(Float, nullable=True, comment="流通市值(万元)")
    total_mv: Mapped[float | None] = mapped_column(Float, nullable=True, comment="总市值(万元)")
    turnover_ratio: Mapped[float | None] = mapped_column(Float, nullable=True, comment="换手率(%)")

    # 封板
    fd_amount: Mapped[float | None] = mapped_column(Float, nullable=True, comment="封单金额(元)")
    first_time: Mapped[str | None] = mapped_column(String(8), nullable=True, comment="首次封板时间(如 093000)")
    last_time: Mapped[str | None] = mapped_column(String(8), nullable=True, comment="最后封板时间")

    # 涨停属性
    open_times: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="炸板次数")
    up_stat: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="涨停统计")
    limit_times: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="连板数")
    limit_type: Mapped[str] = mapped_column(String(8), nullable=False, comment="D=跌停/U=涨停/Z=炸板 — 文档字段 limit")

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint(
            "trade_date", "symbol", "limit_type",
            name="uq_capital_limit_list_d_uk",
        ),
        Index("ix_capital_limit_list_d_trade_date", "trade_date"),
        Index("ix_capital_limit_list_d_symbol", "symbol"),
        Index("ix_capital_limit_list_d_symbol_date", "symbol", "trade_date"),
        Index("ix_capital_limit_list_d_type_date", "limit_type", "trade_date"),
    )

    def __repr__(self) -> str:
        return f"<CapitalLimitListDDB {self.trade_date} {self.symbol} {self.limit_type}>"


__all__ = ["CapitalLimitListDDB"]
