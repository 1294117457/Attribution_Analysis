"""资金流向仓储实现（cap_moneyflows）"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from domain.entitys.cap_moneyflow.entity import CapMoneyflow
from domain.entitys.cap_moneyflow.repository import CapMoneyflowRepository
from infrastructure.persistence.models.cap_moneyflow import CapMoneyflowDB
from infrastructure.persistence.repositories._symboled_dated_repo import (
    find_by_symbol_and_date_range,
    save_batch_symboled_dated,
)


_VALUE_COLUMNS = [
    "buy_sm_vol", "buy_sm_amount", "sell_sm_vol", "sell_sm_amount",
    "buy_md_vol", "buy_md_amount", "sell_md_vol", "sell_md_amount",
    "buy_lg_vol", "buy_lg_amount", "sell_lg_vol", "sell_lg_amount",
    "buy_elg_vol", "buy_elg_amount", "sell_elg_vol", "sell_elg_amount",
    "net_mf_vol", "net_mf_amount", "data_source",
]
_UK = "uq_cap_moneyflow_symbol_date"


class CapMoneyflowRepoImpl:
    """资金流向仓储实现"""

    def __init__(self, session: AsyncSession):
        self._session = session

    @staticmethod
    def _to_entity(row: CapMoneyflowDB) -> CapMoneyflow:
        return CapMoneyflow(
            id=row.id,
            symbol=row.symbol,
            trade_date=row.trade_date,
            data_source=row.data_source,
            buy_sm_vol=row.buy_sm_vol, buy_sm_amount=row.buy_sm_amount,
            sell_sm_vol=row.sell_sm_vol, sell_sm_amount=row.sell_sm_amount,
            buy_md_vol=row.buy_md_vol, buy_md_amount=row.buy_md_amount,
            sell_md_vol=row.sell_md_vol, sell_md_amount=row.sell_md_amount,
            buy_lg_vol=row.buy_lg_vol, buy_lg_amount=row.buy_lg_amount,
            sell_lg_vol=row.sell_lg_vol, sell_lg_amount=row.sell_lg_amount,
            buy_elg_vol=row.buy_elg_vol, buy_elg_amount=row.buy_elg_amount,
            sell_elg_vol=row.sell_elg_vol, sell_elg_amount=row.sell_elg_amount,
            net_mf_vol=row.net_mf_vol, net_mf_amount=row.net_mf_amount,
        )

    async def save(self, entity: CapMoneyflow) -> CapMoneyflow:
        await self.save_batch([entity])
        return entity

    async def save_batch(self, entities: list[CapMoneyflow]) -> int:
        return await save_batch_symboled_dated(
            self._session, CapMoneyflowDB, entities, _VALUE_COLUMNS, _UK,
        )

    async def find_by_symbol(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[CapMoneyflow]:
        rows = await find_by_symbol_and_date_range(
            self._session, CapMoneyflowDB, symbol, start_date, end_date,
        )
        return [self._to_entity(r) for r in rows]


CapMoneyflowRepoImpl.__implements_protocol__ = CapMoneyflowRepository