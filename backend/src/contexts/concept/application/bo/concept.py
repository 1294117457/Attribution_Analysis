"""bo - from contexts/data/application/port (step7-c)"""
from __future__ import annotations

from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from shared.interface.validators import IndexCode
from contexts.collect.application.port.params import EmptyParams, IndexCodeParams, SymbolParams


def _clean_text(v):
    """清洗字符串：去掉换行/制表，首尾空白"""
    if not isinstance(v, str):
        return v
    for noise in ("\n", "\r", "\t"):
        v = v.replace(noise, "")
    return v.strip()


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
    # §2.10 补 Adata concept_constituent_ths 文档 short_name 字段
    short_name: Optional[str] = Field(default=None, max_length=50)
    # 该接口文档无 reason 字段（注意别误加）




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
    """概念当前行情快照（§1.7 字段语义修复）"""

    index_code: str
    # §1.7 修复：change 是涨跌额（元）→ 表里叫 p_change；change_pct 是涨跌幅(%) → 表里叫 pct_change
    p_change: Optional[float] = None        # 涨跌额(元) — Adata 文档 change
    pct_change: Optional[float] = None      # 涨跌幅(%) — Adata 文档 change_pct
    price: Optional[float] = None
    open_price: Optional[float] = None      # 表里叫 open_price
    high: Optional[float] = None
    low: Optional[float] = None
    prev_close: Optional[float] = None
    volume: Optional[float] = None
    amount: Optional[float] = None
    turnover_rate: Optional[float] = None
    pe: Optional[float] = None
    pb: Optional[float] = None
    trade_time: Optional[str] = None
    # §1.7 补 Adata 文档 trade_date + concept_name（业务需要）
    trade_date: Optional[date] = None
    concept_name: Optional[str] = None




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


