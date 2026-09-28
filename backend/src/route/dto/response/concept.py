"""概念相关 DTO

配套设计文档：
  docs/dev/06gainian/03-application-and-route-design.md §1
  docs/dev/step2/02datamanage/04-概念数据adata同源改造方案.md §5.5
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
#  请求 DTO
# ═══════════════════════════════════════════════════════════════════════════════


class ConceptQueryRequest(BaseModel):
    """概念列表查询请求"""
    q: Optional[str] = Field(None, description="模糊搜索概念名称，或精确匹配 index_code")
    is_active: Optional[bool] = Field(None, description="是否有效")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")


# ═══════════════════════════════════════════════════════════════════════════════
#  响应 DTO
# ═══════════════════════════════════════════════════════════════════════════════


class ConceptItemVO(BaseModel):
    """概念列表项 VO"""
    concept_id: int
    index_code: str
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
    reason: Optional[str] = None

    model_config = {"from_attributes": True}


class ConceptLiveVO(BaseModel):
    """概念实时反查 VO（同花顺 F10，不入库）

    与 ConceptItemVO 的区别：
    - ConceptItemVO：库中的概念（concept_id / stock_count / is_active）
    - ConceptLiveVO：实时数据（concept_code / reason，无 concept_id）
    """
    concept_code: str            # 同花顺指数编码，如 "885525"
    name: str                    # 如 "白酒概念"
    source: str                  # "ths"
    reason: Optional[str] = None # 入选理由

    model_config = {"from_attributes": True}


class ConceptDetailVO(ConceptItemVO):
    """概念详情（含成分股）"""
    members: list[ConceptMemberVO] = Field(default_factory=list)


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

    - is_merged: 是否经过实时合并（merge_live=true 时为 true）
    - last_merged_at: 合并时间（仅 is_merged=true 时有值）
    """
    symbol: str
    stock_name: str                   # 抽屉顶部用
    sections: list[ConceptTabSectionVO]   # 已按预定顺序排好
    total_count: int                  # 用于「共 N 个概念」统计
    is_merged: bool = False
    last_merged_at: Optional[datetime] = None


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


# ═══════════════════════════════════════════════════════════════════════════════
#  行情 VO
# ═══════════════════════════════════════════════════════════════════════════════


class ConceptSnapshotVO(BaseModel):
    """概念行情快照 VO（前端涨跌染色 + 概念详情卡片用）

    涨跌幅由快照任务用现价 / 昨收（概念指数日 K）计算，缺昨收时为 None。
    """

    concept_name: str
    pct_change: Optional[float] = None
    rank_current: Optional[int] = None
    rank_total: Optional[int] = None
    rank_label: str = ""                   # "191/390"
    up_count: Optional[int] = None
    down_count: Optional[int] = None
    up_down_label: str = ""
    net_inflow_yi: Optional[float] = None
    turnover_yi: Optional[float] = None
    color: str = "flat"                    # up / down / flat
    captured_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_dict(cls, d: dict) -> "ConceptSnapshotVO":
        return cls(**{k: v for k, v in d.items() if k in cls.model_fields})


class ConceptIndexTHVO(BaseModel):
    """概念指数日 K VO"""

    concept_name: str
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    change: Optional[float] = None
    change_pct: Optional[float] = None

    model_config = {"from_attributes": True}
