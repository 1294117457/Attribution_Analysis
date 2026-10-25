"""TradeCalendarRepository：交易日历读取（表 tech_trade_cal @ raw_data_db）

DailyService 按区间采集时，需要把 [start, end] 换算成真实交易日列表：
N 个交易日 = N 次 Tushare 请求 = 日志进度里的 total 分母。

★ session 由 service 层持有、以参数传入（同 tech 其余 repo）。
  本 repo 不做"退化到周一~周五"的兜底 —— 那是业务决策，留在 service 层；
  这里只负责"如实读日历"，读不到就抛异常。
"""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.market.infrastructure.persistence.models.mkt_calendar import (
    MktCalendarDB,
)

logger = logging.getLogger(__name__)


class TradeCalendarRepository:
    """交易日历仓储（只读）"""

    async def list_trade_dates(
        self, start: date, end: date, session: AsyncSession,
    ) -> list[date]:
        """返回 [start, end] 内的所有开市日（升序、去重）

        - 不按 exchange 过滤：多个交易所的日历通过 distinct() 合并
        - 日历表无数据时返回 []（由 service 决定如何兜底）

        Raises:
            SQLAlchemyError: 查询失败（表不存在 / 连接异常）——由 service
                捕获后 rollback 并退化到工作日近似
        """
        rows = (
            await session.execute(
                select(MktCalendarDB.cal_date)
                .where(MktCalendarDB.cal_date >= start)
                .where(MktCalendarDB.cal_date <= end)
                .where(MktCalendarDB.is_open.is_(True))
                .distinct()
                .order_by(MktCalendarDB.cal_date)
            )
        ).scalars().all()
        return [d for d in rows if d]


__all__ = ["TradeCalendarRepository"]