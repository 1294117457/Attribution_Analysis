"""概念相关 DTO

配套设计文档：
  docs/dev/06gainian/03-application-and-route-design.md §1
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
#  请求 DTO
# ═══════════════════════════════════════════════════════════════════════════════


class ConceptQueryRequest(BaseModel):
    """概念列表查询请求"""
    q: Optional[str] = Field(None, description="模糊搜索概念名称")
    source: Optional[str] = Field(None, description="数据源：em / ths")
    is_active: Optional[bool] = Field(None, description="是否有效")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")


class ConceptSyncRequest(BaseModel):
    """概念同步请求"""
    source: str = Field("em", description="数据源：em / ths")
    concept_names: Optional[list[str]] = Field(
        None, description="指定概念名称列表，为空则全量同步"
    )
    force_resync: bool = Field(False, description="是否强制重同步已有概念")


# ═══════════════════════════════════════════════════════════════════════════════
#  响应 DTO
# ═══════════════════════════════════════════════════════════════════════════════


class ConceptItemVO(BaseModel):
    """概念详情 VO"""
    concept_id: int
    name: str
    source: str
    concept_type: str
    stock_count: int
    description: Optional[str] = None
    is_active: bool
    last_synced_at: Optional[datetime] = None
    first_seen_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ConceptMemberVO(BaseModel):
    """概念成员 VO（成分股）"""
    symbol: str
    name: str
    rank: Optional[int] = None
    latest_price: Optional[float] = None

    model_config = {"from_attributes": True}


class ConceptDetailVO(ConceptItemVO):
    """概念详情（含成分股）"""
    members: list[ConceptMemberVO] = Field(default_factory=list)


class ConceptSyncResultVO(BaseModel):
    """同步结果 VO"""
    total_concepts: int
    total_members: int
    failed_concepts: list[str]
    elapsed_ms: int
    synced_at: datetime


class ConceptTabSectionVO(BaseModel):
    """概念 Tab 单个分组区块

    渲染策略：每个 concept_type 一行标题 + 一组 Tag。
    标题顺序：industry → theme → style → region → event → other（业务约定）。
    """
    type: str               # industry / theme / style / region / event / other
    type_label: str         # 行业概念 / 主题概念 / ...
    concepts: list[dict]    # ConceptGroupedVO 序列化为 dict（避免循环依赖）


class ConceptTabContentVO(BaseModel):
    """概念 Tab 完整渲染模型

    前端 ConceptTab.vue 直接消费，无需再做分组。
    """
    symbol: str
    stock_name: str                   # 抽屉顶部用
    sections: list[ConceptTabSectionVO]   # 已按预定顺序排好
    total_count: int                  # 用于「共 N 个概念」统计


# ═══════════════════════════════════════════════════════════════════════════════
#  类型映射
# ═══════════════════════════════════════════════════════════════════════════════


CONCEPT_TYPE_LABELS: dict[str, str] = {
    "industry": "行业概念",
    "theme":    "主题概念",
    "style":    "风格概念",
    "region":   "地域概念",
    "event":    "事件概念",
    "other":    "其他概念",
}

CONCEPT_TYPE_ORDER: list[str] = [
    "industry", "theme", "style", "region", "event", "other",
]
