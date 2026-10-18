"""采集 Job 模板 — 请求 DTO

PR2 重构（2026-10-15）：合并原 CollectPlanSaveRequest + CollectPlanItemSave 为 CollectJobSaveRequest
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class CollectJobSaveRequest(BaseModel):
    """采集 Job 模板保存（新建 / 更新同一份结构）

    语义：
    - mode=once：一次性执行，不入调度
    - mode=time：每日定时；schedule_type='time' + times 必填
    - mode=interval：固定频率；schedule_type='interval' + interval_seconds 必填
    """
    task_type: str = Field(..., max_length=64, description="采集接口的 task_type")
    display_name: Optional[str] = Field(None, max_length=128, description="显示名；默认 = task_type")
    mode: Literal["once", "time", "interval"] = Field("once", description="触发方式")
    concurrency: int = Field(1, ge=1, le=32, description="并发数（1~32）")
    enabled: bool = Field(True, description="是否启用（禁用后不入调度）")
    schedule_type: Optional[Literal["time", "interval"]] = Field(
        None, description="调度方式；mode∈{time,interval} 时必填",
    )
    times: list[str] = Field(
        default_factory=list,
        description="每日定时的时间点，如 ['09:30','15:00']（24 小时制、HH:MM）",
    )
    interval_seconds: Optional[int] = Field(
        None, ge=30, description="固定频率的间隔秒数（下限 30）",
    )
    stop_on_fail: bool = Field(True, description="单次执行内某单元失败是否中断")
    params: dict = Field(default_factory=dict, description="采集参数（覆盖 default_params）")


__all__ = ["CollectJobSaveRequest"]