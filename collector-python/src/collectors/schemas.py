# 采集数据载体（原 application/bo/* 5 文件合并：BO 只是 pydantic 校验层，无业务逻辑）。
from __future__ import annotations

# -------------------- 原 bo/capital.py --------------------
"""capital 类 BO（资金流、融资融券、龙虎榜、大宗交易、股东数）"""


from datetime import date
from typing import Optional

from pydantic import BaseModel


class CapMoneyflowBO(BaseModel):
    symbol: str
    trade_date: date
    buy_sm_vol: Optional[float] = None
    buy_sm_amount: Optional[float] = None
    sell_sm_vol: Optional[float] = None
    sell_sm_amount: Optional[float] = None
    buy_md_vol: Optional[float] = None
    buy_md_amount: Optional[float] = None
    sell_md_vol: Optional[float] = None
    sell_md_amount: Optional[float] = None
    buy_lg_vol: Optional[float] = None
    buy_lg_amount: Optional[float] = None
    sell_lg_vol: Optional[float] = None
    sell_lg_amount: Optional[float] = None
    buy_elg_vol: Optional[float] = None
    buy_elg_amount: Optional[float] = None
    sell_elg_vol: Optional[float] = None
    sell_elg_amount: Optional[float] = None
    net_mf_vol: Optional[float] = None
    net_mf_amount: Optional[float] = None


class CapMarginDetailBO(BaseModel):
    symbol: str
    trade_date: date
    rzye: Optional[float] = None
    rqye: Optional[float] = None
    rzmre: Optional[float] = None
    rqyl: Optional[float] = None
    rzche: Optional[float] = None
    rqchl: Optional[float] = None
    rqmcl: Optional[float] = None
    rzrqye: Optional[float] = None


class CapTopListBO(BaseModel):
    trade_date: date
    symbol: str
    name: Optional[str] = None
    reason: Optional[str] = None
    close: Optional[float] = None
    pct_change: Optional[float] = None
    turnover_rate: Optional[float] = None
    amount: Optional[float] = None
    l_sell: Optional[float] = None
    l_buy: Optional[float] = None
    l_amount: Optional[float] = None
    net_amount: Optional[float] = None
    net_rate: Optional[float] = None
    amount_rate: Optional[float] = None
    float_values: Optional[float] = None


class CapTopInstBO(BaseModel):
    trade_date: date
    symbol: str
    exalter: Optional[str] = None
    side: Optional[str] = None
    reason: Optional[str] = None
    buy: Optional[float] = None
    buy_rate: Optional[float] = None
    sell: Optional[float] = None
    sell_rate: Optional[float] = None
    net_buy: Optional[float] = None


class CapBlockTradeBO(BaseModel):
    trade_date: date
    symbol: str
    name: Optional[str] = None
    price: Optional[float] = None
    vol: Optional[float] = None
    amount: Optional[float] = None
    buyer: Optional[str] = None
    seller: Optional[str] = None


class CapHolderNumBO(BaseModel):
    symbol: str
    ann_date: Optional[date] = None
    end_date: date
    holder_num: Optional[int] = None
    holder_nums: Optional[float] = None


class CapHsgtTop10BO(BaseModel):
    """沪深股通每日十大成交股（Tushare hsgt_top10 官方结构）"""
    trade_date: date
    symbol: str
    name: Optional[str] = None
    market_type: str
    rank: int
    close: Optional[float] = None
    change: Optional[float] = None
    amount: Optional[float] = None
    net_amount: Optional[float] = None
    buy: Optional[float] = None
    sell: Optional[float] = None


class CapMoneyflowHsgtBO(BaseModel):
    """沪深港通资金流向（Tushare moneyflow_hsgt 官方结构：一行=一个交易日）"""
    trade_date: date
    ggt_ss: Optional[float] = None
    ggt_sz: Optional[float] = None
    hgt: Optional[float] = None
    sgt: Optional[float] = None
    north_money: Optional[float] = None
    south_money: Optional[float] = None


class CapLimitListBO(BaseModel):
    """每日涨跌停板（Tushare limit_list_d 官方结构）"""
    trade_date: date
    symbol: str
    name: Optional[str] = None
    industry: Optional[str] = None
    close: Optional[float] = None
    pct_chg: Optional[float] = None
    amount: Optional[float] = None
    turnover_ratio: Optional[float] = None
    float_mv: Optional[float] = None
    total_mv: Optional[float] = None
    limit_type: str
    limit_times: Optional[int] = None
    open_times: Optional[int] = None
    up_stat: Optional[str] = None
    limit_amount: Optional[float] = None
    fd_amount: Optional[float] = None
    first_time: Optional[str] = None
    last_time: Optional[str] = None


__all__ = [
    "CapMoneyflowBO", "CapMarginDetailBO", "CapTopListBO", "CapTopInstBO",
    "CapBlockTradeBO", "CapHolderNumBO",
    "CapHsgtTop10BO", "CapMoneyflowHsgtBO", "CapLimitListBO",
]

# -------------------- 原 bo/fundamental.py --------------------
"""fundamental 类 BO（每日指标、财报、十大股东）"""


from datetime import date
from typing import Optional

from pydantic import BaseModel


class FinDailyBasicBO(BaseModel):
    symbol: str
    trade_date: date
    close: Optional[float] = None
    turnover_rate: Optional[float] = None
    turnover_rate_f: Optional[float] = None
    volume_ratio: Optional[float] = None
    pe: Optional[float] = None
    pe_ttm: Optional[float] = None
    pb: Optional[float] = None
    ps: Optional[float] = None
    ps_ttm: Optional[float] = None
    dv_ratio: Optional[float] = None
    dv_ttm: Optional[float] = None
    total_share: Optional[float] = None
    float_share: Optional[float] = None
    free_share: Optional[float] = None
    total_mv: Optional[float] = None
    circ_mv: Optional[float] = None


class FinReportBO(BaseModel):
    symbol: str
    end_date: date
    ann_date: Optional[date] = None
    report_type: Optional[str] = None
    comp_type: Optional[str] = None
    basic_eps: Optional[float] = None
    diluted_eps: Optional[float] = None
    total_revenue: Optional[float] = None
    revenue: Optional[float] = None
    operate_profit: Optional[float] = None
    total_profit: Optional[float] = None
    n_income: Optional[float] = None
    n_income_attr_p: Optional[float] = None


class FinTop10HoldersBO(BaseModel):
    symbol: str
    ann_date: Optional[date] = None
    end_date: Optional[date] = None
    holder_name: str
    hold_amount: Optional[float] = None
    hold_ratio: Optional[float] = None
    hold_float_ratio: Optional[float] = None
    hold_change: Optional[float] = None
    holder_type: Optional[str] = None


class FinTop10FloatHoldersBO(BaseModel):
    symbol: str
    ann_date: Optional[date] = None
    end_date: Optional[date] = None
    holder_name: str
    hold_amount: Optional[float] = None
    hold_ratio: Optional[float] = None
    hold_change: Optional[float] = None
    holder_type: Optional[str] = None


__all__ = [
    "FinDailyBasicBO", "FinReportBO",
    "FinTop10HoldersBO", "FinTop10FloatHoldersBO",
]

# -------------------- 原 bo/tech.py --------------------
"""tech / base 类 BO（K 线、复权因子、停牌、名称变更、分红）"""


from datetime import date
from typing import Optional

from pydantic import BaseModel


class BaseAdjFactorBO(BaseModel):
    symbol: str
    trade_date: date
    adj_factor: float


class BaseSuspendBO(BaseModel):
    symbol: str
    trade_date: date
    suspend_timing: Optional[date] = None
    suspend_type: Optional[str] = None


class BaseNameChangeBO(BaseModel):
    symbol: str
    name: str
    start_date: date
    end_date: Optional[date] = None
    ann_date: Optional[date] = None
    change_reason: Optional[str] = None


class BaseDividendBO(BaseModel):
    symbol: str
    end_date: date
    ann_date: Optional[date] = None
    record_date: Optional[date] = None
    ex_date: Optional[date] = None
    pay_date: Optional[date] = None
    div_proc: Optional[str] = None
    stk_div: Optional[float] = None
    stk_bo_rate: Optional[float] = None
    stk_co_rate: Optional[float] = None
    cash_div: Optional[float] = None
    cash_div_tax: Optional[float] = None


__all__ = [
    "BaseAdjFactorBO", "BaseSuspendBO", "BaseNameChangeBO", "BaseDividendBO",
]

# -------------------- 原 bo/kline_compat.py --------------------
"""collect 自有 K 线 BO（从 market 摘出，collector 独立后不再跨上下文 import）。"""

from datetime import date, datetime
from enum import StrEnum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class KlineBO(BaseModel):
    symbol: str = Field(..., description="股票代码")
    trade_date: Optional[date] = None
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: int = Field(..., ge=0, description="成交量（股）")
    amount: float = Field(..., ge=0.0, description="成交额（元）")
    change_pct: Optional[float] = Field(default=None, description="涨跌幅 %")
    name: Optional[str] = Field(default=None, description="股票名称（可选）")
    source: str = Field(default="tushare", description="数据源")

    model_config = {"from_attributes": True}


class MinuteKlineBO(BaseModel):
    symbol: str
    name: str = ""
    dt: datetime
    interval: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float


class MinuteKlineParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str
    interval: str = "5min"
    days: int = 1


class MinuteInterval(StrEnum):
    M1 = "1min"
    M5 = "5min"
    M15 = "15min"
    M30 = "30min"
    M60 = "60min"


BARS_PER_DAY: dict[MinuteInterval, int] = {
    MinuteInterval.M1: 240,
    MinuteInterval.M5: 48,
    MinuteInterval.M15: 16,
    MinuteInterval.M30: 8,
    MinuteInterval.M60: 4,
}


__all__ = [
    "KlineBO", "MinuteKlineBO", "MinuteKlineParams", "MinuteInterval",
    "BARS_PER_DAY",
]

# -------------------- 原 bo/stock_info_compat.py --------------------
"""collect 自有 StockInfo BO（从 market 摘出）。"""

from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class StockInfoBO(BaseModel):
    symbol: str = Field(..., description="股票代码（6位）")
    ts_code: Optional[str] = Field(None, description="Tushare 统一代码")
    name: str = Field("", description="股票名称")
    area: Optional[str] = Field(None, description="地域")
    industry: Optional[str] = Field(None, description="行业")
    market: Optional[str] = Field(None, description="市场类型")
    exchange: Optional[str] = Field(None, description="交易所 SSE/SZSE/BSE")
    list_date: Optional[date] = Field(None, description="上市日期")
    delist_date: Optional[date] = Field(None, description="退市日期")
    list_status: Optional[str] = Field("L", description="上市状态 L/D/P")
    is_hs: Optional[str] = Field("N", description="沪深港通 N/H/S")
    act_name: Optional[str] = Field(None, description="实控人名称")
    act_ent_type: Optional[str] = Field(None, description="实控人企业性质")


__all__ = ["StockInfoBO"]
