"""概念 Port（同花顺概念，以 index_code 885xxx 为业务键）"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from contexts.data.application.port.base import CachePolicy, DataPort
from contexts.data.application.port.types import EmptyParams, IndexCode, IndexCodeParams, SymbolParams

from contexts.concept.domain.concept.bo import ConceptListBO, ConceptMemberBO, ConceptOfStockBO, ConceptIndexTHBO, ConceptSnapshotBO, ConceptMinutePoint, ConceptMinuteBO

def _clean_text(v):
    if not isinstance(v, str):
        return v
    for noise in ("\n", "\r", "\t"):
        v = v.replace(noise, "")
    return v.strip()

# ═══════════════════════════════════════════════════════════════════════════════
# BO
# ═══════════════════════════════════════════════════════════════════════════════

class ConceptIndexDailyParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index_code: IndexCode
    concept_name: str = ""             # 仅用于填充 BO.concept_name

# ═══════════════════════════════════════════════════════════════════════════════
# Port
# ═══════════════════════════════════════════════════════════════════════════════

class ConceptListPort(DataPort[EmptyParams, ConceptListBO]):
    name, label = "concept_list", "概念清单"
    facet, sub_facet = "fundamental", "concept"
    description = "同花顺全部概念（约 390 个）"
    Params, Item = EmptyParams, ConceptListBO

class ConceptMembersPort(DataPort[IndexCodeParams, ConceptMemberBO]):
    name, label = "concept_members", "概念成分股"
    facet, sub_facet = "fundamental", "concept"
    description = "按概念拉成分股；接口正常但无数据返回空列表"
    Params, Item = IndexCodeParams, ConceptMemberBO
    unit = "index_code"
    sample_params = {"index_code": "885525"}

class StockConceptsPort(DataPort[SymbolParams, ConceptOfStockBO]):
    name, label = "stock_concepts", "股票所属概念"
    facet, sub_facet = "fundamental", "concept"
    description = "同花顺 F10 股票所属概念（带入选理由）"
    Params, Item = SymbolParams, ConceptOfStockBO
    unit = "symbol"
    sample_params = {"symbol": "600519"}

class ConceptIndexDailyPort(DataPort[ConceptIndexDailyParams, ConceptIndexTHBO]):
    name, label = "concept_index_daily", "概念指数日 K"
    facet, sub_facet = "fundamental", "concept"
    description = "概念指数日 K + 涨跌幅（全部历史）"
    Params, Item = ConceptIndexDailyParams, ConceptIndexTHBO
    unit = "index_code"
    sample_params = {"index_code": "885525"}

class ConceptSnapshotPort(DataPort[IndexCodeParams, ConceptSnapshotBO]):
    name, label = "concept_snapshot", "概念行情快照"
    facet, sub_facet = "fundamental", "concept"
    description = "概念当前行情快照"
    Params, Item = IndexCodeParams, ConceptSnapshotBO
    unit = "index_code"
    sample_params = {"index_code": "885525"}

class ConceptMinutePort(DataPort[IndexCodeParams, ConceptMinuteBO]):
    name, label = "concept_minute", "概念实时行情"
    facet, sub_facet = "fundamental", "concept"
    description = "同花顺概念当日分时（241 点）+ 最新涨跌幅；失败时降级为最近一条日 K 收盘"
    Params, Item = IndexCodeParams, ConceptMinuteBO
    cache = CachePolicy(ttl_trading=15, consumers=("详情抽屉 · 概念 Tab",))
    sample_params = {"index_code": "885525"}
    sort_order = 10

__all__ = [
    "ConceptIndexDailyParams",
    "ConceptIndexDailyPort",
    "ConceptIndexTHBO",
    "ConceptListBO",
    "ConceptListPort",
    "ConceptMemberBO",
    "ConceptMembersPort",
    "ConceptMinuteBO",
    "ConceptMinutePoint",
    "ConceptMinutePort",
    "ConceptOfStockBO",
    "ConceptSnapshotBO",
    "ConceptSnapshotPort",
    "StockConceptsPort",
]
