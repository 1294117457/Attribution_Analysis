"""StockNameRepository：股票代码 → 名称映射（表 fundamental_stock_basic @ raw_data_db）

DailyService 采集全市场时，fetcher 解析出的 KlineBO.name 是空串
（pro.daily 不返回名称），tech_daily.name 列需要从 stock_basic 补齐。
一次采集任务只需读一次 → service 层缓存成 dict 后逐单元复用。

★ session 由 service 层持有、以参数传入（同 tech 其余 repo）。
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.market.infrastructure.persistence.models.stock_basic import (
    StockBasicDB,
)

logger = logging.getLogger(__name__)


class StockNameRepository:
    """股票名称映射仓储（只读）"""

    async def list_name_map(self, session: AsyncSession) -> dict[str, str]:
        """全市场 symbol(6位) → name

        用于 tech_daily.name 列；查不到 / 表不存在由 service 降级为空 dict，
        此时入库 name 退化为 symbol 本身，不阻断采集。
        """
        rows = (await session.execute(
            select(StockBasicDB.symbol, StockBasicDB.name)
        )).all()
        return {
            str(s).zfill(6): (n or "")
            for s, n in rows
            if s
        }


__all__ = ["StockNameRepository"]