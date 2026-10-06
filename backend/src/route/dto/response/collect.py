"""采集任务管理 — 响应 DTO

配套设计文档：
  docs/dev/step2/02datamanage/01-采集管理四维重构方案.md §2.7
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class TaskDefResponse(BaseModel):
    """采集任务元数据（catalog 接口的元素）"""

    task_type: str = Field(..., description="task_type 唯一键")
    label: str = Field(..., description="UI 显示名（中文）")
    description: str = Field(default="", description="一句话说明（UI 副标题）")
    status: Literal["ready", "planned"] = Field(
        default="ready",
        description="ready: 已实现 / planned: 待实现",
    )
    default_params: dict = Field(default_factory=dict, description="接口默认参数")
    supports_run_one: bool = Field(default=False, description="是否支持按单元同步调用（业务复用）")
    kind: Literal["batch", "realtime"] = Field(default="batch", description="batch: 采集入库 / realtime: 按需查询 + 缓存")
    source: Optional[str] = Field(default=None, description="实时接口数据源分组 ths / tdx")
    source_label: Optional[str] = None
    ttl_trading: Optional[int] = Field(default=None, description="实时接口交易时段缓存秒数")
    consumers: list[str] = Field(default_factory=list, description="实时接口的业务调用方")


class FacetGroupResponse(BaseModel):
    """采集任务目录树（一个面）

    sub_groups 字典的 key 是 sub_facet（如 kline / valuation / margin ...），
    value 是该子分组下的 TaskDefResponse 列表。
    """

    facet: str = Field(..., description="tech / capital / fundamental / news / market")
    label: str = Field(..., description="技术面 / 资金面 / 基本面 / 新闻面 / 市场全局")
    icon: str = Field(default="", description="element-plus icon 名")
    sort_order: int = Field(default=0, description="UI 排序（升序）")
    sub_groups: dict[str, list[TaskDefResponse]] = Field(
        default_factory=dict,
        description="sub_facet → [TaskDefResponse]，按 sub_facet 字典序",
    )


class CollectCatalogResponse(BaseModel):
    """GET /collect/catalog 响应"""

    items: list[FacetGroupResponse] = Field(
        default_factory=list,
        description="按 facet 预设顺序排序的目录树",
    )


# ═══════════════════════════════════════════════════════════════════════
#  采集接口元数据 / 采集方案
# ═══════════════════════════════════════════════════════════════════════


class CollectFetcherResponse(BaseModel):
    """采集接口元数据（代码的 DB 镜像，collect_fetchers 表）"""

    task_type: str = Field(..., description="与代码 registry 的 key 一致")
    label: str = Field(default="", description="UI 显示名（中文）")
    facet: str = Field(default="", description="四大面：tech / capital / fundamental / news")
    sub_facet: str = Field(default="", description="子分组 key")
    description: str = Field(default="", description="一句话说明")
    kind: Literal["batch", "realtime"] = Field(
        default="batch",
        description="batch: 采集任务（可入方案） / realtime: 实时接口（不可入方案）",
    )
    status: Literal["ready", "planned", "orphan"] = Field(
        default="ready",
        description="ready: 可执行 / planned: 占位未实现 / orphan: DB 有但代码已删",
    )
    default_params: dict = Field(default_factory=dict, description="接口默认参数")
    supports_run_one: bool = Field(default=False, description="是否支持按单元同步调用")
    sort_order: int = Field(default=0, description="catalog 排序（升序）")


class CollectPlanItemResponse(BaseModel):
    """采集方案项：方案包含的一个采集接口"""

    id: int = Field(..., description="方案项 id")
    task_type: str = Field(..., description="采集接口 task_type")
    label: str = Field(default="", description="接口显示名（便于 UI 展示）")
    params: dict = Field(default_factory=dict, description="覆盖 default_params 的参数")
    enabled: bool = Field(default=True, description="单项停用开关")
    sort_order: int = Field(default=0, description="执行顺序（升序）")


class CollectPlanResponse(BaseModel):
    """采集方案（触发配置 + 接口编排）"""

    id: int = Field(..., description="方案 id")
    name: str = Field(..., description="方案名称")
    enabled: bool = Field(default=False, description="是否启用定时")
    schedule_type: Optional[Literal["time", "interval"]] = Field(
        default=None, description="None = 仅手动 / time = 每日定时 / interval = 固定频率",
    )
    times: list[str] = Field(default_factory=list, description="每日定时的触发时间点（HH:MM）")
    interval_seconds: Optional[int] = Field(default=None, description="固定频率的间隔秒数")
    stop_on_fail: bool = Field(default=True, description="某项失败后中断后续项")
    items: list[CollectPlanItemResponse] = Field(
        default_factory=list, description="按顺序串行执行的采集接口",
    )
    last_run_at: Optional[str] = Field(default=None, description="上次执行时间")
    last_task_id: Optional[int] = Field(default=None, description="上次执行的第一项 task_id")
    next_run_at: Optional[str] = Field(default=None, description="下次触发时间（APScheduler）")
    created_at: Optional[str] = Field(default=None)
    updated_at: Optional[str] = Field(default=None)