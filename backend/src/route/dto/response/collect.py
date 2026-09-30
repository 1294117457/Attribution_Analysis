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