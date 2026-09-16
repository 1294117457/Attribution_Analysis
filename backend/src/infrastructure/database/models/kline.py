"""日 K 线 ORM 模型（含技术指标展宽字段）"""

from datetime import date
from sqlalchemy import String, Float, Integer, Date, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class DailyKlineDB(Base, TimestampMixin):
    """日K线数据库模型（PO）

    展宽了 17 个技术指标列（方案 A）。
    一行 = (symbol, date) → 当日 OHLC + 17 个派生指标。
    数据规模：23 年 ~3000 万行（无压力），每行 ~150 字节。
    """

    __tablename__ = "daily_klines"

    # ── K 线基础字段 ─────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── 技术指标（方案 A：展宽到 K 线表）──────────────────
    # 均线
    ma5:  Mapped[float | None] = mapped_column(Float, nullable=True)
    ma10: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma20: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma60: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 指数移动平均
    ema12: Mapped[float | None] = mapped_column(Float, nullable=True)
    ema26: Mapped[float | None] = mapped_column(Float, nullable=True)
    # MACD
    macd_dif: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_dea: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_bar: Mapped[float | None] = mapped_column(Float, nullable=True)
    # RSI
    rsi6:  Mapped[float | None] = mapped_column(Float, nullable=True)
    rsi12: Mapped[float | None] = mapped_column(Float, nullable=True)
    rsi24: Mapped[float | None] = mapped_column(Float, nullable=True)
    # KDJ
    kdj_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    kdj_d: Mapped[float | None] = mapped_column(Float, nullable=True)
    kdj_j: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 布林带
    boll_up:  Mapped[float | None] = mapped_column(Float, nullable=True)
    boll_mid: Mapped[float | None] = mapped_column(Float, nullable=True)
    boll_dn:  Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_kline_symbol_date"),
        Index("ix_kline_symbol_date", "symbol", "date"),
    )

    def __repr__(self) -> str:
        return f"<DailyKlineDB {self.symbol} {self.date} close={self.close}>"