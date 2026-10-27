"""CollectLog ORM — 通用操作日志表（表 collect_logs @ attribution_db）

对应表: collect_logs
设计说明：
    - 主键 id 使用 UUID（log_id），由 log_util 同步生成
    - status 状态机: init → running → success / failed / partial_fail
    - updated_at 由 onupdate 自动维护

★ 通用化（2026-10-26）：
    本表原先是「采集日志专用表」（字段名带采集语义：facet / kind / params），
    现抽象为**通用操作日志表**，字段语义与具体业务解耦：

        service_name  → 谁在执行（采集 service / 其他业务动作）
        category      → 分组维度（采集时是 tech/capital/...，其他场景可自定义）
        action        → 动作类型（采集时是 incremental/full_refresh/realtime）
        meta          → 动态上下文（JSONB，采集时存原始入参）
        trigger_*     → 触发来源与触发者
        status        → 生命周期状态（init/running/success/partial_fail/failed/skipped）
        progress + 4 个计数 → 进度与统计（通用，任何长任务都能用）
        duration_ms   → 耗时（通用）

    ★ 动态内容一律放 meta(JSONB)，计数/进度保持标量 ——
      前端强依赖 saved_count / fail_count / total_count / progress 这几个标量，
      塞进 JSONB 会让前端取值和 DB 统计索引都变复杂。

迁移说明（2026-10-26）：
    - 本文件从 `contexts/collect/infrastructure/persistence/models/collect_log.py`
      迁到 `shared/infrastructure/persistence/models/`。
      原因：collect_logs 是**跨 context 的公共元数据表**（操作日志），
      配套的 log_util 落在 shared/infrastructure/ 下，
      若 ORM 留在 contexts/collect/ 会形成 shared → contexts 的反向依赖，
      破坏 DDD 分层方向。
    - 字段改名 facet→category / kind→action / params→meta，
      由迁移脚本 `backend/sql/migrate_collect_logs.sql` 执行 RENAME COLUMN。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.persistence.orm_base import AttribBase


class CollectLogDB(AttribBase):
    """通用操作日志 ORM"""

    __tablename__ = "collect_logs"

    # 主键
    id: Mapped[str] = mapped_column(UUID(), primary_key=True)  # log_id，UUID

    # 执行者 / 分组维度
    service_name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)

    # 触发信息
    trigger_source: Mapped[str] = mapped_column(
        String(32), nullable=False, default="manual",
    )
    trigger_user: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True,
    )

    # 动态上下文（JSONB）—— 采集场景存原始入参
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # 状态机
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="init")

    # 数量统计
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    saved_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 耗时（毫秒）—— 终态时写入
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 错误信息
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 时间
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.now,
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # 元信息
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now(),
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
