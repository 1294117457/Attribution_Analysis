"""CollectLog ORM — 采集日志表

对应表: collect_logs
设计说明：
    - 主键 id 使用 UUID（log_id），由 handler 同步生成
    - status 状态机: pending → running → success/partial_fail/failed/skipped
    - updated_at 由数据库触发器自动维护

参考文档：docs/backend-docs/dev/level2/step1采集模块优化/06采集日志进度优化/01-采集日志进度优化方案.md §二
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.orm_base import Base


class CollectLogDB(Base):
    """采集日志 ORM"""
    __tablename__ = "collect_logs"
    
    # 主键
    id: Mapped[str] = mapped_column(UUID(), primary_key=True)  # log_id，UUID
    
    # 采集服务标识
    service_name: Mapped[str] = mapped_column(String(128), nullable=False)
    facet: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    
    # 触发信息
    trigger_source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    trigger_user: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # 采集参数
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    
    # 状态机
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    
    # 数量统计
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    saved_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # 错误信息
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 时间
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.now
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # 元信息
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    
    __table_args__ = (
        Index("idx_collect_logs_service_name", "service_name"),
        Index("idx_collect_logs_status", "status"),
        Index("idx_collect_logs_started_at", started_at.desc()),
        Index("idx_collect_logs_service_time", "service_name", started_at.desc()),
    )
    
    def __repr__(self) -> str:
        return f"<CollectLog {self.id} {self.service_name} {self.status}>"


__all__ = ["CollectLogDB"]
