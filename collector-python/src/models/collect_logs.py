"""采集任务日志 ORM 模型（PG attribution 库；collector 写、Java 只读）。

表名: collect_logs（复数）
主键: task_id（hex，由 Collector 生成，与 Redis key collect:task:{id} 一致）
写入: 三态 —— INSERT queued → UPDATE running → UPDATE 终态
中间进度只写 Redis，不碰本表。

规范见 backend-java/docs/开发文档/采集模块/采集模块现状文档（三类采集：增量-全量覆盖-实时查询）.md §5.3
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import AttribBase
from core.db import TimestampMixin


class CollectLogDB(AttribBase, TimestampMixin):
    """采集任务日志（一行 = 一次 POST /tasks 建任务请求）

    归属 attribution 业务库 → 必须用 db_session_factory()，禁止 raw_session_factory()。
    """

    __tablename__ = "collect_logs"

    # ── 身份与定位 ──────────────────────────────────────
    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    facet: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="condition")

    # ── 触发来源（审计）────────────────────────────────
    trigger_source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    trigger_user: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ── 采集参数（审计）────────────────────────────────
    params_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    range_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    range_end: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── 状态机 ─────────────────────────────────────────
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── 计数器（步数口径：一次 collect() 调用 = 1 步）──
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    done: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fail: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skip: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── 计数器（行数口径：写入 raw_data 的行）──────────
    saved_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── 结果信息 ───────────────────────────────────────
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # ── 时间（全部 timestamptz）────────────────────────
    # 注意：started_at / finished_at 不走 TimestampMixin（它只管 created_at / updated_at）
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # ★ duration_ms = finished_at - started_at（毫秒）
    #   ⚠️ 必须声明！log_repo.mark_finished() 会写这一列，
    #      未映射的列在 SQLAlchemy update().values() 里会抛
    #      "expected to update N column(s), got N+1" → 终态永远写不进去。
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── 中断支持 ───────────────────────────────────────
    cancel_requested: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    parent_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_collect_logs_name_status", "name", "status"),
        Index("ix_collect_logs_facet", "facet"),
        Index("ix_collect_logs_created", "created_at"),
        Index("ix_collect_logs_status_created", "status", "created_at"),
        Index("ix_collect_logs_trigger_source", "trigger_source", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<CollectLogDB {self.task_id} {self.name} {self.status}>"


__all__ = ["CollectLogDB"]
