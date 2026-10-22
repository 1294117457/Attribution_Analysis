"""财务报表（利润表）ORM 模型

表名：fundamental_income（对齐 Tushare 接口名 pro.income）
UK: (symbol, end_date, report_type)
"""

from datetime import date
from sqlalchemy import String, Float, Date, Index, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.orm_base import RawBase
from shared.infrastructure.persistence.mixins import TimestampMixin


class FinReportDB(RawBase, TimestampMixin):
    """利润表（Tushare pro.income）

    UK: (symbol, end_date, report_type)
    """

    __tablename__ = "fundamental_income"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    ann_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    report_type: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="报表类型(Tushare): 1=合并报表 2=单季合并 6=母公司报表…，本项目只采 1")
    comp_type: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="公司类型: 1=一般工商业 2=银行 3=保险 4=证券 7=多元金融")

    # 利润表核心字段
    basic_eps: Mapped[float | None] = mapped_column(Float, nullable=True, comment="基本每股收益")
    diluted_eps: Mapped[float | None] = mapped_column(Float, nullable=True, comment="稀释每股收益")
    total_revenue: Mapped[float | None] = mapped_column(Float, nullable=True, comment="营业总收入")
    revenue: Mapped[float | None] = mapped_column(Float, nullable=True, comment="营业收入")
    operate_profit: Mapped[float | None] = mapped_column(Float, nullable=True, comment="营业利润")
    total_profit: Mapped[float | None] = mapped_column(Float, nullable=True, comment="利润总额")
    n_income: Mapped[float | None] = mapped_column(Float, nullable=True, comment="净利润")
    n_income_attr_p: Mapped[float | None] = mapped_column(Float, nullable=True, comment="归属母公司股东的净利润")

    # 资产负债核心字段
    total_assets: Mapped[float | None] = mapped_column(Float, nullable=True, comment="资产总计")
    total_liab: Mapped[float | None] = mapped_column(Float, nullable=True, comment="负债合计")
    total_hldr_eqy_exc_min_int: Mapped[float | None] = mapped_column(Float, nullable=True, comment="归属母公司股东权益")

    # 现金流量核心字段
    n_cashflow_act: Mapped[float | None] = mapped_column(Float, nullable=True, comment="经营活动现金流量净额")
    n_cash_flows_fnc_act: Mapped[float | None] = mapped_column(Float, nullable=True, comment="筹资活动现金流量净额")
    n_cashflow_inv_act: Mapped[float | None] = mapped_column(Float, nullable=True, comment="投资活动现金流量净额")

    # §4.7 补 Tushare income 文档 end_type 字段
    end_type: Mapped[str | None] = mapped_column(String(8), nullable=True, comment="报告期类型(Q1/Q2/Q3/Q4/半年报/年报)")

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("symbol", "end_date", "report_type", name="uq_fundamental_income_uk"),
        Index("ix_fundamental_income_symbol_end", "symbol", "end_date"),
    )

    def __repr__(self) -> str:
        return f"<FinReportDB {self.symbol} {self.end_date}>"
