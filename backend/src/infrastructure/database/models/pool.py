"""操作池 ORM 模型"""

from datetime import datetime
from sqlalchemy import (
    String, Integer, Boolean, Text,
    ForeignKey, Index, JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class StockPoolDB(Base, TimestampMixin):
    """操作池 ORM 模型"""

    __tablename__ = "stock_pools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pool_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="custom", index=True,
    )
    color: Mapped[str | None] = mapped_column(String(16), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True,
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    owner_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    share_token: Mapped[str | None] = mapped_column(String(64), nullable=True)

    members: Mapped[list["StockPoolMemberDB"]] = relationship(
        back_populates="pool",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    operations: Mapped[list["PoolOperationDB"]] = relationship(
        back_populates="pool",
        passive_deletes=True,
        lazy="select",
    )

    __table_args__ = (
        Index("ix_stock_pools_updated_at", "updated_at"),
    )

    def __repr__(self) -> str:
        return f"<StockPoolDB {self.id} {self.name}>"


class StockPoolMemberDB(Base):
    """池成员 ORM 模型"""

    __tablename__ = "stock_pool_members"

    pool_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("stock_pools.id", ondelete="CASCADE"),
        primary_key=True,
    )
    symbol: Mapped[str] = mapped_column(String(10), primary_key=True, index=True)
    memo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    added_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.now)

    pool: Mapped["StockPoolDB"] = relationship(back_populates="members")

    def __repr__(self) -> str:
        return f"<StockPoolMemberDB {self.pool_id}:{self.symbol}>"


class PoolOperationDB(Base):
    """池操作记录 ORM 模型"""

    __tablename__ = "pool_operations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pool_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("stock_pools.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    operation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", index=True,
    )
    params: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict,
    )
    result_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    progress: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=lambda: {"done": 0, "total": 0, "failed": 0},
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.now)

    pool: Mapped["StockPoolDB | None"] = relationship(back_populates="operations")

    __table_args__ = (
        Index("ix_pool_operations_type_status", "operation_type", "status"),
        Index("ix_pool_operations_created_at", "created_at"),
        Index("ix_pool_operations_pool_time", "pool_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<PoolOperationDB {self.id} {self.operation_type} {self.status}>"
