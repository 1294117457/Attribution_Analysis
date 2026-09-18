"""采集任务日志 ORM 模型"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Text, DateTime, Index, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class SysCollectTaskDB(Base, TimestampMixin):
    """采集任务主表"""
    __tablename__ = "sys_collect_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_type: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    skip_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_sys_collect_tasks_type_time", "task_type", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<SysCollectTask {self.id} {self.task_type} {self.status}>"


class SysCollectTaskDetailDB(Base):
    """采集任务明细表"""
    __tablename__ = "sys_collect_task_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    saved_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<SysCollectTaskDetail {self.id} task={self.task_id} {self.symbol} {self.status}>"
