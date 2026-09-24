"""StockPanel 组合行 — 4 表快照的不可变值对象

设计要点：
- frozen=True：值对象创建后不可变，保证面板行的"快照"语义
- 字段来源清晰标注，跨域组合但不归属任何单一聚合根
- 与 application/dto/panel.py::StockPanelItemVO 字段 1:1 对齐
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class StockPanelRow:
    """股票列表面板行快照（4 表 JOIN / 子查询结果）

    来源：
    - stock_infos           基本字段 13 个
    - tech_kline_dailys     K 线统计 3 个（COUNT / MIN / MAX）
    - fin_daily_basics      最新一行估值 3 个（close / total_mv / pe_ttm）
    - fin_reports           最新一期净利润率 1 个（n_income / revenue × 100）

    用途：仅用于"列表面板"视图投影，不可写回任何源表。
    属于 domain/panel 上下文，不归属任何单一聚合根。
    """

    # ── 来自 stock_infos ─────────────────────────────
    symbol: str
    ts_code: Optional[str]
    name: Optional[str]
    area: Optional[str]
    industry: Optional[str]
    market: Optional[str]
    exchange: Optional[str]
    list_date: Optional[str]          # YYYYMMDD 字符串
    list_status: Optional[str]
    is_hs: Optional[str]
    act_name: Optional[str]
    act_ent_type: Optional[str]
    total_shares: Optional[int]

    # ── 来自 tech_kline_dailys（聚合） ──────────────
    record_count: int
    kline_start: Optional[date]
    kline_end: Optional[date]

    # ── 来自 fin_daily_basics（最新一行） ─────────────
    latest_close: Optional[float]
    total_mv: Optional[float]
    pe_ttm: Optional[float]

    # ── 来自 fin_reports（最新一期） ─────────────
    profit_margin: Optional[float]