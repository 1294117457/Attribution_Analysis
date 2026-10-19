"""股票所属概念 ORM 模型（Adata get_concept_ths 接口）

接口: adata.stock.info.get_concept_ths
物理表名: fundamental_stock_concept
UK: (symbol, concept_id)
"""

from datetime import datetime
from sqlalchemy import String, Text, DateTime, Index, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.orm_base import RawBase
from shared.infrastructure.persistence.mixins import TimestampMixin


class FundamentalStockConceptDB(RawBase, TimestampMixin):
    """股票所属概念（Adata get_concept_ths 接口）

    一行 = (symbol, concept_id) 单只股票包含的某个概念及原因。
    与 fundamental_concept_member 形成"概念视角"和"股票视角"互补。
    """

    __tablename__ = "fundamental_stock_concept"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    concept_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="关联 fundamental_concept.id")
    name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="冗余概念名(便于查询)")

    source: Mapped[str] = mapped_column(String(10), nullable=False, default="ths")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="纳入该概念的原因")

    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.now,
    )

    __table_args__ = (
        UniqueConstraint("symbol", "concept_id", name="uq_fundamental_stock_concept_uk"),
        Index("ix_fundamental_stock_concept_symbol", "symbol"),
        Index("ix_fundamental_stock_concept_concept_id", "concept_id"),
    )

    def __repr__(self) -> str:
        return f"<FundamentalStockConceptDB {self.symbol} concept={self.concept_id}>"


__all__ = ["FundamentalStockConceptDB"]
