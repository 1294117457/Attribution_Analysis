"""股票基本信息 ORM 模型

表名：fundamental_stock_basic（对齐 Tushare 接口名 pro.stock_basic）
类名：StockBasicDB

★ 字段与接口返回参一一对应（Tushare stock_basic 输出参数共 17 列）：
    ts_code / symbol / name / area / industry / fullname / enname / cnspell
    / market / exchange / curr_type / list_status / list_date / delist_date
    / is_hs / act_name / act_ent_type

  另有 4 个非接口字段（入库基础设施，不参与接口对账）：
    id         自增主键
    created_at / updated_at  行版本时间戳

★ 已删除 total_shares：接口文档明确「旧版上的 PE/PB/股本等字段请在
  每日指标接口(daily_basic)获取」，股本字段不属于 stock_basic 返回参。
"""

from datetime import date
from sqlalchemy import String, Integer, Date, Index
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.orm_base import RawBase
from shared.infrastructure.persistence.mixins import TimestampMixin


class StockBasicDB(RawBase, TimestampMixin):
    """股票基本信息数据库模型（PO）

    一行 = 一只股票（symbol 唯一）。
    列名 = Tushare stock_basic 输出参数名，不做改写。
    """

    __tablename__ = "fundamental_stock_basic"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── 接口输出参数（顺序对齐接口文档） ──────────────────────
    ts_code: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True,
        comment="TS代码",
    )
    symbol: Mapped[str] = mapped_column(
        String(10), unique=True, nullable=False, index=True,
        comment="股票代码",
    )
    name: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    area: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True,
        comment="地域",
    )
    industry: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True,
        comment="所属行业",
    )
    fullname: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
        comment="股票全称",
    )
    enname: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
        comment="英文全称",
    )
    cnspell: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
        comment="拼音缩写",
    )
    market: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True,
        comment="市场类型（主板/创业板/科创板/CDR）",
    )
    exchange: Mapped[str | None] = mapped_column(
        String(10), nullable=True, index=True,
        comment="交易所代码 SSE/SZSE/BSE",
    )
    curr_type: Mapped[str | None] = mapped_column(
        String(8), nullable=True,
        comment="交易货币",
    )
    list_status: Mapped[str | None] = mapped_column(
        String(5), nullable=True, default="L", index=True,
        comment="上市状态 L/D/G/P/UN",
    )
    list_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    delist_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_hs: Mapped[str | None] = mapped_column(
        String(5), nullable=True, default="N",
        comment="沪深港通 N/H/S",
    )
    act_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
        comment="实控人名称",
    )
    act_ent_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="实控人企业性质",
    )

    __table_args__ = (
        Index("ix_stock_basic_industry_market", "industry", "market"),
        Index("ix_stock_basic_exchange_status", "exchange", "list_status"),
    )

    def __repr__(self) -> str:
        return f"<StockBasicDB {self.symbol} {self.name}>"


__all__ = ["StockBasicDB"]
