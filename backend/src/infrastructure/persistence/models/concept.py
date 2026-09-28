"""概念板块 ORM 模型（adata · 同花顺）

全链路以同花顺指数编码 index_code（885xxx）为业务键，name 只用于展示。

配套设计文档：
  docs/dev/step2/02datamanage/04-概念数据adata同源改造方案.md §4
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.persistence.base import Base


class ConceptsDB(Base):
    """概念聚合根 ORM"""

    __tablename__ = "concepts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    index_code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    concept_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="ths")
    concept_type: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    stock_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.now
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_concepts_name", "name"),
        Index("ix_concepts_active", "is_active", postgresql_where=is_active == True),  # noqa: E712
    )

    def __repr__(self) -> str:
        return f"<ConceptsDB(id={self.id}, index_code={self.index_code!r}, name={self.name!r})>"


class ConceptMemberDB(Base):
    """概念成员关联表 ORM（股票 ↔ 概念 M:N）"""

    __tablename__ = "stock_concept_members"

    symbol: Mapped[str] = mapped_column(String(10), primary_key=True)
    concept_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.now
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.now
    )
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="ths")

    __table_args__ = (
        Index("ix_concept_member_symbol", "symbol"),
        Index("ix_concept_member_concept", "concept_id"),
    )

    def __repr__(self) -> str:
        return f"<ConceptMemberDB(symbol={self.symbol!r}, concept_id={self.concept_id})>"


class ConceptSnapshotDB(Base):
    """概念行情快照 ORM

    时序数据：每批采集每个概念写入 1 行（保留历史）。
    应用层取最新 1 行：ORDER BY captured_at DESC LIMIT 1。
    """

    __tablename__ = "concept_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    index_code: Mapped[str] = mapped_column(String(10), nullable=False)
    concept_name: Mapped[str] = mapped_column(String(100), nullable=False)
    trade_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    open_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    high: Mapped[float | None] = mapped_column(Float, nullable=True)
    low: Mapped[float | None] = mapped_column(Float, nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    prev_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    rank_current: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rank_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    up_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    down_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    volume_wan: Mapped[float | None] = mapped_column(Float, nullable=True)
    turnover_yi: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_inflow_yi: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="ths")
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.now,
    )

    __table_args__ = (
        Index("ix_concept_snapshots_code_captured", "index_code", "captured_at"),
        Index("ix_concept_snapshots_name_captured", "concept_name", "captured_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ConceptSnapshotDB(code={self.index_code!r}, "
            f"pct_change={self.pct_change}, captured_at={self.captured_at})>"
        )


class ConceptIndexTHDB(Base):
    """概念指数日 K ORM

    每个 (index_code, trade_date) 唯一，ON CONFLICT DO UPDATE。
    """

    __tablename__ = "concept_index_ths"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    index_code: Mapped[str] = mapped_column(String(10), nullable=False)
    concept_name: Mapped[str] = mapped_column(String(100), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    high: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    low: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    close: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    change: Mapped[float | None] = mapped_column(Float, nullable=True)
    change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.now,
    )

    __table_args__ = (
        UniqueConstraint("index_code", "trade_date", name="uq_concept_index_th_code_date"),
        Index("ix_concept_index_th_name", "concept_name"),
        Index("ix_concept_index_th_date", "trade_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<ConceptIndexTHDB(code={self.index_code!r}, "
            f"date={self.trade_date}, close={self.close})>"
        )
