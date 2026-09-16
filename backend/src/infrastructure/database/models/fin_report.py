"""财务报表 ORM 模型"""

from datetime import date
from sqlalchemy import String, Float, Date, Index, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class FinReportDB(Base, TimestampMixin):
    """财务报表（利润表/资产负债表/现金流量表）

    物理表名: fin_reports
    UK: (symbol, end_date)
    """

    __tablename__ = "fin_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    ann_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    report_type: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="报表类型: 1=合并报表/2=母公司报表")
    comp_type: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="公司类型: 1=工商业/2=金融/3=保险")

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

    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="tushare")

    __table_args__ = (
        UniqueConstraint("symbol", "end_date", "report_type", name="uq_fin_reports_uk"),
        Index("ix_fin_reports_symbol_end", "symbol", "end_date"),
    )

    def __repr__(self) -> str:
        return f"<FinReportDB {self.symbol} {self.end_date}>"
