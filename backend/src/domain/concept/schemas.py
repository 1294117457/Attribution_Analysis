"""概念 BO（采集层 → 应用层）

配套设计文档：
  docs/dev/06gainian/01-domain-design.md §3
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from domain.concept.entity import Concept, ConceptSource, ConceptType


class ConceptListBO(BaseModel):
    """概念清单 BO（来自 ak.stock_board_concept_name_em）

    字段说明：
    - 东方财富接口实际字段：排名 / 板块名称 / 板块代码 / 最新价 / 涨跌额 / 涨跌幅 /
      总市值 / 换手率 / 上涨家数 / 下跌家数 / 领涨股票 / 板块代码
    - 我们只关心：name / code / stock_count（成分股数量）
    """

    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=20, description="板块代码")
    source: ConceptSource = Field(default=ConceptSource.EM)
    concept_type: ConceptType = Field(default=ConceptType.OTHER)
    stock_count: int = Field(default=0, ge=0)
    description: Optional[str] = Field(default=None, max_length=500)
    raw_payload: Optional[dict] = Field(default=None, description="原始 dict（调试用）")

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        """概念名称标准化：去前后空格、去除常见噪声字符"""
        if not isinstance(v, str):
            return v
        v = v.strip()
        # 东方财富偶尔返回 "人形机器人\n" 这种，剔除
        for noise in ("\n", "\r", "\t"):
            v = v.replace(noise, "")
        return v

    def to_entity(self) -> Concept:
        """BO → Entity"""
        return Concept.create(
            name=self.name,
            source=self.source,
            concept_type=self.concept_type,
            description=self.description,
        )


class ConceptStockBO(BaseModel):
    """概念成分股 BO（来自 ak.stock_board_concept_cons_em(symbol=name)）

    字段说明：
    - 东方财富接口实际字段：序号 / 代码 / 名称 / 最新价 / 涨跌幅 / 涨跌额 / 成交量 /
      成交额 / 振幅 / 最高 / 最低 / 今开 / 昨收 / 市盈率 / 市净率
    - 我们只关心：symbol / name / rank（序号）
    """

    symbol: str = Field(..., min_length=6, max_length=6)
    name: str = Field(..., min_length=1, max_length=100)
    source: ConceptSource = Field(default=ConceptSource.EM)
    rank: Optional[int] = Field(default=None, description="在该概念中的排名")
    latest_price: Optional[float] = Field(default=None)

    @field_validator("symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        return v.strip().zfill(6)

    def to_entity(self, concept_id: int) -> "ConceptMember":
        from domain.concept.entity import ConceptMember
        return ConceptMember.create(
            symbol=self.symbol,
            concept_id=concept_id,
            source=self.source,
        )
