"""概念 Port（同花顺概念，以 index_code 885xxx 为业务键）"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from application.port.data.base import CachePolicy, DataPort
from application.port.data.types import EmptyParams, IndexCode, IndexCodeParams, SymbolParams


def _clean_text(v):
    if not isinstance(v, str):
        return v
    for noise in ("\n", "\r", "\t"):
        v = v.replace(noise, "")
    return v.strip()


# ═══════════════════════════════════════════════════════════════════════════════
# BO
# ═══════════════════════════════════════════════════════════════════════════════


class ConceptListBO(BaseModel):
    """概念清单行"""

    index_code: str = Field(..., min_length=6, max_length=10, description="同花顺指数编码 885xxx")
    concept_code: Optional[str] = Field(default=None, max_length=10, description="同花顺网页编码 30xxxx")
    name: str = Field(..., min_length=1, max_length=100)

    _normalize_name = field_validator("name", mode="before")(_clean_text)


class ConceptMemberBO(BaseModel):
    """概念成分股一行"""

    index_code: str
    symbol: str = Field(..., min_length=6, max_length=6)


class ConceptOfStockBO(BaseModel):
    """股票所属概念（带入选理由）"""

    symbol: str = Field(..., min_length=6, max_length=6)
    index_code: str = Field(..., min_length=1, max_length=10)
    name: str = Field(..., min_length=1, max_length=100)
    reason: Optional[str] = Field(default=None, description="入选理由")

    _normalize_name = field_validator("name", mode="before")(_clean_text)


class ConceptIndexTHBO(BaseModel):
    """概念指数日 K"""

    index_code: str
    concept_name: str = ""
    trade_date: date
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = Field(default=0, ge=0)
    amount: float = Field(default=0.0, ge=0.0)
    change: Optional[float] = None
    change_pct: Optional[float] = None


class ConceptSnapshotBO(BaseModel):
    """概念当前行情快照"""

    index_code: str
    price: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    volume: Optional[float] = None
    amount: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    prev_close: Optional[float] = None
    turnover_rate: Optional[float] = None
    pe: Optional[float] = None
    pb: Optional[float] = None
    trade_time: Optional[str] = None


class ConceptMinutePoint(BaseModel):
    """概念日分时的一个点"""

    trade_time: str
    price: float
    avg_price: Optional[float] = None
    volume: Optional[int] = None
    amount: Optional[float] = None
    change_pct: Optional[float] = None


class ConceptMinuteBO(BaseModel):
    """概念日分时：pre_close 由首个有效点 price - change 推算；price / change / change_pct 取最后一个点"""

    index_code: str
    trade_date: Optional[str] = None
    pre_close: Optional[float] = None
    price: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    trade_time: Optional[str] = None
    points: list[ConceptMinutePoint] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# Params
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
