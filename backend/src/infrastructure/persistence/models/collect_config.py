"""采集方案 / 采集任务组 ORM 模型"""
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.persistence.base import Base
from infrastructure.persistence.mixins import TimestampMixin


class CollectPlanDB(Base, TimestampMixin):
    """采集方案：每个 task_type 一条（默认参数 + 定时 + 启停）"""
    __tablename__ = "collect_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cron: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    trading_day_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    last_task_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<CollectPlan {self.task_type} enabled={self.enabled} cron={self.cron}>"


class CollectGroupDB(Base, TimestampMixin):
    """采集任务组：按 items 顺序串行执行多个采集接口"""
    __tablename__ = "collect_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    # [{"task_type": "stock_basic", "params": {}}, ...]
    items: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cron: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    trading_day_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    stop_on_fail: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    last_group_run_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<CollectGroup {self.id} {self.name}>"
