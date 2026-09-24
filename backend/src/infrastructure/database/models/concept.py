"""概念板块 ORM 模型

配套设计文档：
  docs/dev/06gainian/02-infrastructure-design.md §2
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Index, Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base


class ConceptsDB(Base):
    """概念聚合根 ORM"""

    __tablename__ = "concepts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="em")
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
        Index("ix_concepts_source", "source"),
        # 部分索引：仅对 is_active=TRUE 的行建立索引
        Index("ix_concepts_active", "is_active", postgresql_where=is_active == True),  # noqa: E501
    )

    def __repr__(self) -> str:
        return f"<ConceptsDB(id={self.id}, name={self.name!r}, source={self.source!r})>"


class ConceptMemberDB(Base):
    """概念成员关联表 ORM"""

    __tablename__ = "stock_concept_members"

    symbol: Mapped[str] = mapped_column(String(10), primary_key=True)
    concept_id: Mapped[int] = mapped_column(
        Integer, primary_key=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.now
    )
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="em")

    __table_args__ = (
        Index("ix_concept_member_symbol", "symbol"),
        Index("ix_concept_member_concept", "concept_id"),
    )

    def __repr__(self) -> str:
        return f"<ConceptMemberDB(symbol={self.symbol!r}, concept_id={self.concept_id})>"
