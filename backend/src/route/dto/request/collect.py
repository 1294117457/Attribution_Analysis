"""采集方案 / 采集任务组 — 请求 DTO"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CollectPlanSaveRequest(BaseModel):
    enabled: bool = Field(False, description="是否启用定时")
    cron: Optional[str] = Field(None, description="5 段 crontab（分 时 日 月 周），空 = 仅手动")
    params: dict = Field(default_factory=dict, description="覆盖 default_params 的参数")
    trading_day_only: bool = Field(True, description="仅交易日执行（当前只排除周末）")


class CollectGroupItem(BaseModel):
    task_type: str
    params: dict = Field(default_factory=dict)


class CollectGroupSaveRequest(BaseModel):
    name: str = Field(..., max_length=64)
    items: list[CollectGroupItem] = Field(default_factory=list, description="按顺序串行执行")
    enabled: bool = False
    cron: Optional[str] = None
    trading_day_only: bool = True
    stop_on_fail: bool = Field(True, description="某项 failed / cancelled 后停止后续项")
