"""采集方案 — 请求 DTO"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class CollectPlanItemSave(BaseModel):
    """采集方案项：方案包含的一个采集接口"""
    task_type: str = Field(..., max_length=64, description="采集接口的 task_type")
    params: dict = Field(default_factory=dict, description="覆盖该接口 default_params")
    enabled: bool = Field(True, description="单项停用开关")


class CollectPlanSaveRequest(BaseModel):
    """采集方案保存（新建 / 更新同一份结构）"""
    name: str = Field(..., max_length=64, description="方案名称")
    enabled: bool = Field(False, description="是否启用定时")
    schedule_type: Optional[Literal["time", "interval"]] = Field(
        None, description="触发方式；None = 仅手动"
    )
    times: list[str] = Field(
        default_factory=list,
        description="每日定时的时间点，如 ['09:30','15:00']（24 小时制、HH:MM）",
    )
    interval_seconds: Optional[int] = Field(
        None, description="固定频率的间隔秒数（下限 30）",
    )
    stop_on_fail: bool = Field(True, description="某项失败后中断后续项")
    items: list[CollectPlanItemSave] = Field(
        default_factory=list, description="按顺序串行执行的采集接口",
    )
