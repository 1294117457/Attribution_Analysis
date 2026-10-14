"""原始数据入库（14 张原始表）— 按 Port 名为键的统一入口

实现策略：保留现有 `XxxRepoImpl.save_batch` 写入语义，新增 `_SPECS` 映射表
把"取哪个 Port"映射到"写哪个 Repo"。这样：
  - 14 个声明式任务只声明 port + 元数据，不再 import ORM/Repo
  - 写入策略零变化（cap_top_inst 仍 on_conflict_do_nothing，其他仍按 UK upsert）
  - 现有 `route/api/v1/data_board.py` 仍在用 Repo 读，本次不动

配套设计文档：docs/backend-docs/dev/step5/03collect优化/02-端口与基础设施实现.md §3.1
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from application.port.collect_port import RawDataStorePort
from application.port.data.base import DataPort
from application.port.data.capital import (
    BlockTradePort,
    HolderNumberPort,
    MarginDetailPort,
    MoneyflowPort,
    TopInstPort,
    TopListPort,
)
from application.port.data.fundamental import (
    DailyBasicPort,
    FinIncomePort,
    Top10FloatHoldersPort,
    Top10HoldersPort,
)
from application.port.data.reference import (
    AdjFactorPort,
    DividendPort,
    NameChangePort,
    SuspendPort,
)
from infrastructure.persistence.connection import AsyncSessionLocal
from infrastructure.persistence.models.base_adj_factor import BaseAdjFactorDB
from infrastructure.persistence.models.base_dividend import BaseDividendDB
from infrastructure.persistence.models.base_suspend import BaseSuspendDB
from infrastructure.persistence.models.cap_block_trade import CapBlockTradeDB
from infrastructure.persistence.models.cap_holder_num import CapHolderNumDB
from infrastructure.persistence.models.cap_margin_detail import CapMarginDetailDB
from infrastructure.persistence.models.cap_moneyflow import CapMoneyflowDB
from infrastructure.persistence.models.cap_top_inst import CapTopInstDB
from infrastructure.persistence.models.cap_top_list import CapTopListDB
from infrastructure.persistence.models.fin_daily_basic import FinDailyBasicDB
from infrastructure.persistence.models.fin_report import FinReportDB
from infrastructure.persistence.models.fin_top10_float import FinTop10FloatHolderDB
from infrastructure.persistence.models.fin_top10_holders import FinTop10HolderDB
from infrastructure.persistence.repositories.base_adj_factor_repository import BaseAdjFactorRepoImpl
from infrastructure.persistence.repositories.base_dividend_repository import BaseDividendRepoImpl
from infrastructure.persistence.repositories.base_name_change_repository import BaseNameChangeRepoImpl
from infrastructure.persistence.repositories.base_suspend_repository import BaseSuspendRepoImpl
from infrastructure.persistence.repositories.cap_block_trade_repository import CapBlockTradeRepoImpl
from infrastructure.persistence.repositories.cap_holder_num_repository import CapHolderNumRepoImpl
from infrastructure.persistence.repositories.cap_margin_detail_repository import CapMarginDetailRepoImpl
from infrastructure.persistence.repositories.cap_moneyflow_repository import CapMoneyflowRepoImpl
from infrastructure.persistence.repositories.cap_top_inst_repository import CapTopInstRepoImpl
from infrastructure.persistence.repositories.cap_top_list_repository import CapTopListRepoImpl
from infrastructure.persistence.repositories.fin_daily_basic_repository import FinDailyBasicRepoImpl
from infrastructure.persistence.repositories.fin_report_repository import FinReportRepoImpl
from infrastructure.persistence.repositories.fin_top10_float_repository import FinTop10FloatRepoImpl
from infrastructure.persistence.repositories.fin_top10_holders_repository import FinTop10HoldersRepoImpl
from sqlalchemy import select

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _Spec:
    """单张表的入库规格：写哪个 Repo + 增量列 + 单元类型"""
    repo: type              # 有 save_batch(entities) 的 RepoImpl 类
    column: Any             # 增量列（ORM 列）；None 表示不做增量
    unit: str               # "trade_date" | "symbol"


# 14 条映射与 tushare_tasks.py 原 existing_column / repo 一一对应
_SPECS: dict[str, _Spec] = {
    # 按交易日
    DailyBasicPort.name:         _Spec(FinDailyBasicRepoImpl,    FinDailyBasicDB.trade_date,     "trade_date"),
    SuspendPort.name:            _Spec(BaseSuspendRepoImpl,      BaseSuspendDB.trade_date,       "trade_date"),
    MoneyflowPort.name:          _Spec(CapMoneyflowRepoImpl,     CapMoneyflowDB.trade_date,      "trade_date"),
    MarginDetailPort.name:       _Spec(CapMarginDetailRepoImpl,  CapMarginDetailDB.trade_date,   "trade_date"),
    TopListPort.name:            _Spec(CapTopListRepoImpl,       CapTopListDB.trade_date,        "trade_date"),
    TopInstPort.name:            _Spec(CapTopInstRepoImpl,       CapTopInstDB.trade_date,        "trade_date"),
    BlockTradePort.name:         _Spec(CapBlockTradeRepoImpl,    CapBlockTradeDB.trade_date,     "trade_date"),
    # 按股票
    AdjFactorPort.name:          _Spec(BaseAdjFactorRepoImpl,    BaseAdjFactorDB.symbol,         "symbol"),
    DividendPort.name:           _Spec(BaseDividendRepoImpl,     BaseDividendDB.symbol,          "symbol"),
    HolderNumberPort.name:       _Spec(CapHolderNumRepoImpl,     CapHolderNumDB.symbol,          "symbol"),
    Top10HoldersPort.name:       _Spec(FinTop10HoldersRepoImpl,  FinTop10HolderDB.symbol,        "symbol"),
    Top10FloatHoldersPort.name:  _Spec(FinTop10FloatRepoImpl,    FinTop10FloatHolderDB.symbol,   "symbol"),
    FinIncomePort.name:          _Spec(FinReportRepoImpl,        FinReportDB.symbol,             "symbol"),
    # 全量（无增量列）
    NameChangePort.name:         _Spec(BaseNameChangeRepoImpl,   None,                           "symbol"),
}


class SqlRawDataStore(RawDataStorePort):
    """原始数据入库：14 张表统一入口"""

    def supports(self, port: type[DataPort]) -> bool:
        return port.name in _SPECS

    async def save(self, port: type[DataPort], items: list[Any]) -> int:
        spec = _SPECS[port.name]
        if not items:
            return 0
        entities = [b.to_entity() for b in items]
        async with AsyncSessionLocal() as session:
            return await spec.repo(session).save_batch(entities)

    async def existing(
        self, port: type[DataPort], units: list[str] | None,
    ) -> set[str]:
        spec = _SPECS[port.name]
        column = spec.column
        if column is None:
            return set()
        async with AsyncSessionLocal() as session:
            if units is None:
                rows = await session.execute(select(column).distinct())
                values = [r[0] for r in rows.all()]
            else:
                from application.collect.task import parse_date
                values = [parse_date(u) if spec.unit == "trade_date" else u for u in units]
                rows = await session.execute(
                    select(column).where(column.in_(values)).distinct()
                )
                values = [r[0] for r in rows.all()]
        if spec.unit == "trade_date":
            return {v.strftime("%Y%m%d") for v in values}
        return set(values)


__all__ = ["SqlRawDataStore"]
