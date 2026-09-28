"""概念采集 BO（adata · 同花顺 → 采集任务）

配套设计文档：docs/dev/step2/02datamanage/04-概念数据adata同源改造方案.md §5.2
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


def _clean_text(v):
    if not isinstance(v, str):
        return v
    for noise in ("\n", "\r", "\t"):
        v = v.replace(noise, "")
    return v.strip()


class ConceptListBO(BaseModel):
    """概念清单行（adata.all_concept_code_ths）"""

    index_code: str = Field(..., min_length=6, max_length=10, description="同花顺指数编码 885xxx")
    concept_code: Optional[str] = Field(default=None, max_length=10, description="同花顺网页编码 30xxxx")
    name: str = Field(..., min_length=1, max_length=100)

    _normalize_name = field_validator("name", mode="before")(_clean_text)


class ConceptOfStockBO(BaseModel):
    """股票所属概念（adata.get_concept_ths）

    adata 返回的 concept_code 字段实际是 index_code（885xxx）。
    """

    symbol: str = Field(..., min_length=6, max_length=6)
    index_code: str = Field(..., min_length=1, max_length=10)
    name: str = Field(..., min_length=1, max_length=100)
    reason: Optional[str] = Field(default=None, description="入选理由")

    _normalize_name = field_validator("name", mode="before")(_clean_text)


class ConceptIndexTHBO(BaseModel):
    """概念指数日 K（adata.get_market_concept_ths, k_type=1）"""

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


class ConceptCurrentBO(BaseModel):
    """概念实时行情（adata.get_market_concept_current_ths）；接口不提供涨跌幅"""

    index_code: str
    trade_time: Optional[datetime] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    price: float
    volume: Optional[int] = None
    amount: Optional[float] = None


class ConceptSnapshotBO(BaseModel):
    """概念行情快照（由快照任务用实时行情 + 昨收组装）"""

    index_code: str
    concept_name: str
    trade_time: Optional[datetime] = None
    open_price: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    price: Optional[float] = None
    prev_close: Optional[float] = None
    pct_change: Optional[float] = None
    rank_current: Optional[int] = None
    rank_total: Optional[int] = None
    volume_wan: Optional[float] = None
    turnover_yi: Optional[float] = None
    captured_at: datetime = Field(default_factory=datetime.now)
