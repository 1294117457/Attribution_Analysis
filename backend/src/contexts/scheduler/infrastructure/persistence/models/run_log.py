"""run_log ORM

⚠️ 本期（拆分）保留表名 `collect_run_log`，**不动 DB**。
原因：避免破坏已有 DB 数据；后续 RENAME TABLE 由独立迁移脚本处理。

ORM 类名从 `CollectRunLogDB` → `RunLogDB`（类名跟随模块重命名）。

参考文档：docs/backend-docs/dev/step7/01采集重构/01-精简方案总览.md §3.2
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.orm_base import Base


class RunLogDB(Base):
    """调度运行日志（本期保留表名 collect_run_log）

    1 行 = 1 次 service.collect() 执行
    只追加（除 status/finished_at/duration_ms/counts 字段）
    """
    __tablename__ = "collect_run_log"   # 暂保留（拆模块不改表名）

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # 来源
    schedule_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    service_name: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(16), nullable=False)   # 'schedule' / 'manual' / 'api'

    # 参数（执行时合并后的最终值）
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # 时间
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 结果
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skip_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    saved_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_collect_run_log_service_time", "service_name", "started_at"),
        Index("ix_collect_run_log_status", "status"),
        Index("ix_collect_run_log_schedule", "schedule_id"),
    )

    def __repr__(self) -> str:
        return f"<RunLog {self.id} {self.service_name} {self.status}>"


__all__ = ["RunLogDB"]
