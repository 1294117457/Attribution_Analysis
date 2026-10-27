"""tech / base 类 BO（复权因子、停牌、名称变更、分红）+ daily 采集结果"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from pydantic import BaseModel


@dataclass(frozen=True)
class DailyFetcherResult:
    """单个自然日的采集结果

    ★ 用 model 而非裸元组 —— 裸元组的长度/含义会漂移，
      这正是改造前 daily_service 线上报错的根因
      （_collect_by_date 返回 2 元组，调用方按 3 元组解包 → ValueError）。

    ★ 命名收窄到 Daily：先只针对 daily 跑通，
      不提前抽象成通用的 CollectUnitResult。
    """

    trade_date: date                      # 采集的自然日
    rows: int = 0                        # 实际入库行数
    ok: bool = False                     # 是否成功取到数据
    fail: int = 0                        # 失败数（0 或 1）
    error: str | None = None             # 失败原因

    @property
    def is_empty(self) -> bool:
        """查不到数据 ≠ 失败（周末/节假日/停牌都属空返回）"""
        return self.ok and self.rows == 0


class BaseAdjFactorBO(BaseModel):
    symbol: str
    trade_date: date
    adj_factor: float


class BaseSuspendBO(BaseModel):
    symbol: str
    trade_date: date
    # §2.1 修复：Tushare 文档 suspend_timing 是字符串（如 "09:30-10:00"），不是 date
    suspend_timing: Optional[str] = None
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
    # §2.8 补 Tushare dividend 文档字段
    div_listdate: Optional[date] = None     # 红股上市日
    imp_ann_date: Optional[date] = None     # 实施公告日


__all__ = [
    "DailyFetcherResult",
    "BaseAdjFactorBO", "BaseSuspendBO", "BaseNameChangeBO", "BaseDividendBO",
]
