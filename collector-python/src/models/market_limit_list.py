"""每日涨跌停板 ORM 模型"""

from datetime import date
from sqlalchemy import String, Float, Date, Index, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from core.db import RawBase
from core.db import TimestampMixin


class MarketLimitListDB(RawBase, TimestampMixin):
    """每日涨跌停板

    物理表名: capital_limit_list_d
    UK: (trade_date, symbol, limit_type)
    数据来源: Tushare limit_list_d

    ★ 结构 = Tushare 官方接口列（对齐 collector-python/docs/data/tushare.md 限价板章节）：
      trade_date, ts_code, industry, name, close, pct_chg, amount, limit_amount,
      float_mv, total_mv, turnover_ratio, fd_amount, first_time, last_time,
      open_times, up_stat, limit_times, limit
    ❌ 原 ORM 的 close_price / change_rate / board_count / first_limit_time /
       board_strength / reason 是自造字段，上游**不提供** → 已删除。
       （官方对应字段：close→close、pct_chg→pct_chg、limit_times→连板数、
         first_time→首次封板时间、limit→涨跌停类型）
    ⚠️ 当前 TUSHARE_TOKEN **无该接口权限**（2025-10-29 实测），
       结构仍按官方对齐，采集需账号开通积分权限。
    """

    __tablename__ = "capital_limit_list_d"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # 行情
    close: Mapped[float | None] = mapped_column(Float, nullable=True)          # 收盘价
    pct_chg: Mapped[float | None] = mapped_column(Float, nullable=True)        # 涨跌幅（%）
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)        # 成交额
    turnover_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)  # 换手率
    float_mv: Mapped[float | None] = mapped_column(Float, nullable=True)      # 流通市值
    total_mv: Mapped[float | None] = mapped_column(Float, nullable=True)      # 总市值

    # 涨跌停属性
    limit_type: Mapped[str] = mapped_column(String(8), nullable=False)        # U涨停 D跌停 Z炸板
    limit_times: Mapped[int | None] = mapped_column(Integer, nullable=True)   # 连板数
    open_times: Mapped[int | None] = mapped_column(Integer, nullable=True)    # 炸板次数
    up_stat: Mapped[str | None] = mapped_column(String(16), nullable=True)   # 涨停统计（N/T）
    limit_amount: Mapped[float | None] = mapped_column(Float, nullable=True)  # 板上成交金额
    fd_amount: Mapped[float | None] = mapped_column(Float, nullable=True)    # 封单金额
    first_time: Mapped[str | None] = mapped_column(String(8), nullable=True)  # 首次封板时间
    last_time: Mapped[str | None] = mapped_column(String(8), nullable=True)   # 最后封板时间

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("trade_date", "symbol", "limit_type",
                         name="uq_capital_limit_list_d_uk"),
        Index("ix_capital_limit_list_d_trade_date", "trade_date"),
        Index("ix_capital_limit_list_d_symbol", "symbol"),
        Index("ix_capital_limit_list_d_limit_times", "limit_times"),
    )

    def __repr__(self) -> str:
        return f"<MarketLimitListDB {self.trade_date} {self.symbol} {self.limit_type}>"


__all__ = ["MarketLimitListDB"]
