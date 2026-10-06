"""采集任务日志 ORM 模型

表：
  - sys_collect_tasks      采集任务主表（每次执行一行，任务框架 _finish_task 写入）

注：原 sys_collect_task_details（采集单元明细）表已移除 —— 全库 0 行、0 代码读写，
    单元级进度走 Redis + UnitTally 内存聚合，明细无落地需求。详见 docs 采集管理优化。
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Text, DateTime, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column
from infrastructure.persistence.base import Base
from infrastructure.persistence.mixins import TimestampMixin


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
    # 同一次采集方案执行的各项共享（= 该次第一项的 task_id）
    plan_run_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)

    __table_args__ = (
        Index("ix_sys_collect_tasks_type_time", "task_type", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<SysCollectTask {self.id} {self.task_type} {self.status}>"
