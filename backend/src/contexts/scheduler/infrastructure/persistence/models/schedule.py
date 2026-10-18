"""schedule ORM

⚠️ 本期（拆分）保留表名 `collect_schedule`，**不动 DB**。
原因：避免破坏已有 DB 数据；后续 RENAME TABLE 由独立迁移脚本处理。

ORM 类名从 `CollectScheduleDB` → `ScheduleDB`（类名跟随模块重命名）。

参考文档：docs/backend-docs/dev/step7/01采集重构/01-精简方案总览.md §3.1
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, func, true
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.orm_base import Base


class ScheduleDB(Base):
    """调度计划表（本期保留表名 collect_schedule）

    1 行 = 1 个 service 的定时配置
    """
    __tablename__ = "collect_schedule"   # 暂保留（拆模块不改表名，避免破坏数据）

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # 调度
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    trigger_type: Mapped[str] = mapped_column(String(16), nullable=False)   # 'time' / 'interval'

    # 当 trigger_type='time' 时
    times: Mapped[list] = mapped_column(ARRAY(String), nullable=False, default=list)
    # 当 trigger_type='interval' 时
    interval_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 业务参数（透传给 service.collect）
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # 执行控制
    concurrency: Mapped[int] = mapped_column(Integer, nullable=False, default=5)

    # 描述
    display_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_collect_schedule_enabled", "enabled", postgresql_where=true()),
    )

    def __repr__(self) -> str:
        return f"<Schedule {self.id} {self.service_name} {self.trigger_type}>"


__all__ = ["ScheduleDB"]
