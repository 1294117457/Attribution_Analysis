"""自动迁移自 domain/concept/schemas.py（BO 部分）"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import List, Literal, Optional
from datetime import date, datetime

from domain.entitys.concept.entity import ConceptSource, ConceptType

class ConceptListBO(BaseModel):
    """概念清单 BO

    字段说明：
    - EM 接口 (ak.stock_board_concept_name_em)：
      排名 / 板块名称 / 板块代码 / 最新价 / 涨跌额 / 涨跌幅 /
      总市值 / 换手率 / 上涨家数 / 下跌家数 / 领涨股票 / 板块代码
      我们只关心：name / code / stock_count（成分股数量）
    - THS 接口 (ak.stock_board_concept_name_ths)：
      name / code  (无 stock_count，需要二次请求)
    - adata get_concept_east（按股票反查）：
      stock_code / concept_code / name / source / **reason（入选理由）**
    """

    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=20, description="板块代码")
    source: ConceptSource = Field(default=ConceptSource.EM)
    concept_type: ConceptType = Field(default=ConceptType.OTHER)
    stock_count: int = Field(default=0, ge=0)
    description: Optional[str] = Field(default=None, max_length=500)
    reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="入选理由（adata 独有；如「公司有深圳国资背景。」）",
    )
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
        """BO → Entity

        把 reason 写入 description（如果 description 未设置），便于后续展示。
        避免数据丢失：reason 是 adata 的高价值字段。
        """
        description = self.description
        if not description and self.reason:
            description = self.reason
        return Concept.create(
            name=self.name,
            source=self.source,
            concept_type=self.concept_type,
            description=description,
        )


class ConceptStockBO(BaseModel):
    """概念成分股 BO（来自 ak.stock_board_concept_cons_em(symbol=name)）

    字段说明：
    - 东方财富接口实际字段：序号 / 代码 / 名称 / 最新价 / 涨跌幅 / 涨跌额 / 成交量 /
      成交额 / 振幅 / 最高 / 最低 / 今开 / 昨收 / 市盈率 / 市净率
    - 我们只关心：symbol / name / rank（序号）

    09concept 变更说明：
    - akshare THS 没有「概念→成分股」端点，本类实际使用率下降
    - 数据源标注字段保留 EM 用于兼容历史代码
    """

    symbol: str = Field(..., min_length=6, max_length=6)
    name: str = Field(..., min_length=1, max_length=100)
    source: ConceptSource = Field(default=ConceptSource.THS)  # 09concept: 默认改 THS
    rank: Optional[int] = Field(default=None, description="在该概念中的排名")
    latest_price: Optional[float] = Field(default=None)

    @field_validator("symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        return v.strip().zfill(6)

    def to_entity(self, concept_id: int) -> "ConceptMember":
        from domain.entitys.concept.entity import ConceptMember
        return ConceptMember.create(
            symbol=self.symbol,
            concept_id=concept_id,
            source=self.source,
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  09concept 新增 BO（采集层 → 应用层）
# ═══════════════════════════════════════════════════════════════════════════════


class ConceptSnapshotBO(BaseModel):
    """概念行情快照 BO（ak.stock_board_concept_info_ths）

    字段来自 THS 接口实参：
      板块名称 / 今开 / 昨收 / 最低 / 最高 / 成交量(万手) /
      板块涨幅("X.XX%") / 涨幅排名("191/390") / 涨跌家数("90/372") /
      资金净流入(亿) / 成交额(亿)

    pct_change 保留原始字符串（便于调试），应用层用 to_pct_change() 解析。
    """

    concept_name: str = Field(..., min_length=1, max_length=100)
    open_price: Optional[float] = Field(default=None, description="今开")
    prev_close: Optional[float] = Field(default=None, description="昨收")
    low: Optional[float] = Field(default=None, description="最低")
    high: Optional[float] = Field(default=None, description="最高")
    volume_wan: Optional[float] = Field(default=None, description="成交量(万手)")
    pct_change_raw: str = Field(default="0.00%", description="板块涨幅原始字符串，如 '-1.32%'")
    rank_label: str = Field(default="", description='涨幅排名原始，如 "191/390"')
    up_down_label: str = Field(default="", description='涨跌家数原始，如 "90/372"')
    net_inflow_yi: Optional[float] = Field(default=None, description="资金净流入(亿)")
    turnover_yi: Optional[float] = Field(default=None, description="成交额(亿)")
    rank_current: Optional[int] = Field(default=None, description="排名数字部分：191")
    rank_total: Optional[int] = Field(default=None, description="排名分母部分：390")
    up_count: Optional[int] = Field(default=None, description="上涨家数：90")
    down_count: Optional[int] = Field(default=None, description="下跌家数：372")
    source: ConceptSource = Field(default=ConceptSource.THS)
    captured_at: datetime = Field(default_factory=lambda: datetime.now())

    def to_pct_change(self) -> float:
        """'-1.32%' → -1.32；'+0.5%' → 0.5；'0.00%' → 0.0"""
        s = (self.pct_change_raw or "0%").strip().rstrip("%")
        try:
            return float(s)
        except ValueError:
            return 0.0


class ConceptIndexTHBO(BaseModel):
    """概念指数日 K BO（ak.stock_board_concept_index_ths）

    字段：日期 / 开盘价 / 最高价 / 最低价 / 收盘价 / 成交量 / 成交额
    """

    concept_name: str = Field(..., min_length=1, max_length=100)
    trade_date: date = Field(..., description="交易日")
    open: float = Field(default=0.0, description="开盘价")
    high: float = Field(default=0.0, description="最高价")
    low: float = Field(default=0.0, description="最低价")
    close: float = Field(default=0.0, description="收盘价")
    volume: int = Field(default=0, ge=0, description="成交量")
    amount: float = Field(default=0.0, ge=0.0, description="成交额")
    source: ConceptSource = Field(default=ConceptSource.THS)
    captured_at: datetime = Field(default_factory=lambda: datetime.now())
