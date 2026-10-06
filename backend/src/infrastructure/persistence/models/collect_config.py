"""采集配置 ORM 模型：采集接口元数据 / 采集方案 / 采集方案项"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.persistence.base import Base
from infrastructure.persistence.mixins import TimestampMixin


class CollectFetcherDB(Base, TimestampMixin):
    """采集接口元数据（代码的 DB 镜像，启动期自动对账补录）

    ⚠️ 这张表**不是配置源**，代码里的 CollectTaskRegistry 才是唯一事实来源。
       它的价值是：UI 可展示 / 可做表单驱动的参数 schema / 启动期能发现漂移。
    """
    __tablename__ = "collect_fetchers"

    # 与 CollectTaskRegistry 的 key 一致（batch 任务名 或 realtime 查询名）
    task_type: Mapped[str] = mapped_column(String(64), primary_key=True)
    label: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    facet: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    sub_facet: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    # 'batch'（采集任务，可入方案） / 'realtime'（实时接口，不可入方案）
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="batch")
    # 'ready'（可执行） / 'planned'（占位未实现） / 'orphan'（DB 有但代码已删）
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ready")

    default_params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    supports_run_one: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"<CollectFetcher {self.task_type} kind={self.kind} status={self.status}>"


class CollectPlanDB(Base, TimestampMixin):
    """采集方案：触发配置 + 编排策略

    ⚠️ 一个方案可包含多个采集接口（见 CollectPlanItemDB）。
       方案本身只决定「什么时候触发」「失败了要不要继续」。
    """
    __tablename__ = "collect_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # None = 尚未选择触发方式（仅手动）
    # 'time'     = 每日定时（按 times 里的时间点）
    # 'interval' = 固定频率（按 interval_seconds）
    schedule_type: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    # schedule_type='time' 时生效，形如 ["09:30", "15:00"]，24 小时制、分钟精度
    times: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # schedule_type='interval' 时生效；单位统一存"秒"，秒/分/时只是 UI 换算
    interval_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 某项失败 / 取消后是否中断后续项
    stop_on_fail: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # 上次执行记录；last_task_id = 该次执行第一项的 task_id
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    last_task_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<CollectPlan {self.id} {self.name} enabled={self.enabled}>"


class CollectPlanItemDB(Base, TimestampMixin):
    """采集方案项：方案包含哪些接口 + 各带什么参数 + 执行顺序"""
    __tablename__ = "collect_plan_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("collect_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_type: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("collect_fetchers.task_type"),
        nullable=False,
    )
    params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # 单项临时停用（不动整个方案就能跳过某一项）
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("plan_id", "task_type", name="uq_plan_task_type"),
    )

    def __repr__(self) -> str:
        return f"<CollectPlanItem plan={self.plan_id} {self.task_type} order={self.sort_order}>"


__all__ = [
    "CollectFetcherDB",
    "CollectPlanDB",
    "CollectPlanItemDB",
]
