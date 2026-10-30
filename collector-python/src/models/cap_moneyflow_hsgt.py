"""沪深港通资金流向 ORM 模型（北向 / 南向）"""

from datetime import date
from sqlalchemy import String, Float, Date, Index, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from core.db import RawBase
from core.db import TimestampMixin


class CapMoneyflowHsgtDB(RawBase, TimestampMixin):
    """沪深港通资金流向（北向 / 南向资金）

    物理表名: capital_moneyflow_hsgt
    UK: (trade_date)
    数据来源: Tushare moneyflow_hsgt

    ★ 结构 = Tushare 官方接口列（2025-10-29 实测核对）：
      trade_date, ggt_ss, ggt_sz, hgt, sgt, north_money, south_money
      —— **一行 = 一个交易日的资金流汇总**（不是按股票排行的）
    ❌ 原 ORM 是「按交易所汇总」（exchange / buy_amount / sell_amount），
       与上游和远端表**都对不上** → 已按上游重建。
    ⚠️ 上游 `ggt_ss`/`ggt_sz`/`hgt`/`sgt`/`north_money`/`south_money` 单位为**百万元**。
    """

    __tablename__ = "capital_moneyflow_hsgt"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    trade_date: Mapped[date] = mapped_column(Date, nullable=False)

    # 港股通（南向）
    ggt_ss: Mapped[float | None] = mapped_column(Float, nullable=True)   # 港股通（上海）
    ggt_sz: Mapped[float | None] = mapped_column(Float, nullable=True)   # 港股通（深圳）

    # 陆股通（北向）
    hgt: Mapped[float | None] = mapped_column(Float, nullable=True)      # 沪股通
    sgt: Mapped[float | None] = mapped_column(Float, nullable=True)      # 深股通

    north_money: Mapped[float | None] = mapped_column(Float, nullable=True)  # 北向资金（百万元）
    south_money: Mapped[float | None] = mapped_column(Float, nullable=True)  # 南向资金（百万元）

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("trade_date", name="uq_capital_moneyflow_hsgt_uk"),
        Index("ix_capital_moneyflow_hsgt_trade_date", "trade_date"),
    )

    def __repr__(self) -> str:
        return f"<CapMoneyflowHsgtDB {self.trade_date} north={self.north_money}>"


__all__ = ["CapMoneyflowHsgtDB"]
