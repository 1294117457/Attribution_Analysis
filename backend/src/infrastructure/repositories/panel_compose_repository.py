"""StockPanel 组合查询 — SQLAlchemy 实现

迁移自原 StockRepoImpl.list_with_kline_stats_paginated：
- 主表 stock_infos
- LEFT JOIN tech_kline_dailys 拿 K 线聚合
- 通过子查询拿 fin_daily_basics 每只股票最新一行
- 通过子查询拿 fin_reports 每只股票最新一期（report_type=1）净利润率
- min_total_mv 走 HAVING 过滤

同时承接 PoolRepoImpl.list_membership_by_symbols，
让"列表所需的所有数据"由一个组合仓储一次性提供，
避免服务层跨仓储编排。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.pool import PoolMembershipVO
from domain.panel.repository import StockPanelComposeRepository
from domain.panel.value_objects import StockPanelRow
from infrastructure.database.models.fin_daily_basic import FinDailyBasicDB
from infrastructure.database.models.fin_report import FinReportDB
from infrastructure.database.models.pool import StockPoolDB, StockPoolMemberDB
from infrastructure.database.models.stock_info import StockInfoDB
from infrastructure.database.models.tech_kline import TechKlineDailyDB

if TYPE_CHECKING:
    pass


def _fmt_yyyymmdd(d) -> Optional[str]:
    if d is None:
        return None
    return d.strftime("%Y%m%d")


class StockPanelComposeRepoImpl:
    """列表面板组合仓储实现

    关键点：
    - 主表 stock_infos
    - LEFT JOIN tech_kline_dailys 拿 K 线聚合
    - 通过子查询拿 fin_daily_basics 每只股票最新一行
    - 通过子查询拿 fin_reports 每只股票最新一期（report_type=1）净利润率
    - min_total_mv 走 HAVING 过滤
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    # ── 主查询：4 表快照 + 分页 + 多维筛选 ─────────────────────

    async def list_paginated(
        self,
        q: Optional[str] = None,
        industry: Optional[str] = None,
        market: Optional[str] = None,
        exchange: Optional[str] = None,
        is_hs: Optional[str] = None,
        list_status: Optional[str] = None,
        exclude_st: Optional[bool] = None,
        min_total_mv: Optional[float] = None,
        with_pools: bool = False,  # 当前签名保留以保持 Protocol 兼容
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[StockPanelRow], int]:
        """分页 + 多维筛选 + 4 表快照（K线聚合 + 最新估值 + 最新净利润率）

        with_pools 在本方法中仅作为协议兼容字段保留，
        池信息由调用方通过 list_membership_by_symbols 单独批量反查，
        这样能让"列表快照"和"池反查"两个职责清晰分离。
        """

        # 子查询 1：fin_daily_basics 每只股票最新一行
        latest_date_sq = (
            select(
                FinDailyBasicDB.symbol,
                func.max(FinDailyBasicDB.trade_date).label("max_date"),
            )
            .group_by(FinDailyBasicDB.symbol)
            .subquery("latest_date")
        )
        latest_basic_sq = (
            select(
                FinDailyBasicDB.symbol,
                FinDailyBasicDB.close.label("latest_close"),
                FinDailyBasicDB.total_mv,
                FinDailyBasicDB.pe_ttm,
            )
            .join(
                latest_date_sq,
                and_(
                    FinDailyBasicDB.symbol == latest_date_sq.c.symbol,
                    FinDailyBasicDB.trade_date == latest_date_sq.c.max_date,
                ),
            )
            .subquery("latest_basic")
        )

        # 子查询 2：fin_reports 每只股票最新一期（report_type=1）净利润率
        latest_report_date_sq = (
            select(
                FinReportDB.symbol,
                func.max(FinReportDB.end_date).label("max_end_date"),
            )
            .where(FinReportDB.report_type == "1")
            .group_by(FinReportDB.symbol)
            .subquery("latest_report_date")
        )
        latest_report_sq = (
            select(
                FinReportDB.symbol,
                (
                    FinReportDB.n_income
                    / func.nullif(FinReportDB.revenue, 0)
                    * 100
                ).label("profit_margin"),
            )
            .join(
                latest_report_date_sq,
                and_(
                    FinReportDB.symbol == latest_report_date_sq.c.symbol,
                    FinReportDB.end_date == latest_report_date_sq.c.max_end_date,
                    FinReportDB.report_type == "1",
                ),
            )
            .subquery("latest_report")
        )

        # 主查询：4 表 LEFT JOIN + 聚合
        stmt = (
            select(
                StockInfoDB.symbol,
                StockInfoDB.ts_code,
                StockInfoDB.name,
                StockInfoDB.area,
                StockInfoDB.industry,
                StockInfoDB.market,
                StockInfoDB.exchange,
                StockInfoDB.list_date,
                StockInfoDB.list_status,
                StockInfoDB.is_hs,
                StockInfoDB.act_name,
                StockInfoDB.act_ent_type,
                StockInfoDB.total_shares,
                func.count(TechKlineDailyDB.id).label("record_count"),
                func.min(TechKlineDailyDB.date).label("kline_start"),
                func.max(TechKlineDailyDB.date).label("kline_end"),
                latest_basic_sq.c.latest_close,
                latest_basic_sq.c.total_mv,
                latest_basic_sq.c.pe_ttm,
                latest_report_sq.c.profit_margin,
            )
            .outerjoin(TechKlineDailyDB, StockInfoDB.symbol == TechKlineDailyDB.symbol)
            .outerjoin(latest_basic_sq, StockInfoDB.symbol == latest_basic_sq.c.symbol)
            .outerjoin(latest_report_sq, StockInfoDB.symbol == latest_report_sq.c.symbol)
            .group_by(
                StockInfoDB.symbol,
                StockInfoDB.ts_code,
                StockInfoDB.name,
                StockInfoDB.area,
                StockInfoDB.industry,
                StockInfoDB.market,
                StockInfoDB.exchange,
                StockInfoDB.list_date,
                StockInfoDB.list_status,
                StockInfoDB.is_hs,
                StockInfoDB.act_name,
                StockInfoDB.act_ent_type,
                StockInfoDB.total_shares,
                latest_basic_sq.c.latest_close,
                latest_basic_sq.c.total_mv,
                latest_basic_sq.c.pe_ttm,
                latest_report_sq.c.profit_margin,
            )
        )
        count_stmt = select(func.count()).select_from(StockInfoDB)

        # ── 条件构造 ─────────────────────────────────────
        conditions = []
        if q:
            like = f"%{q}%"
            conditions.append(
                or_(
                    StockInfoDB.symbol.ilike(like),
                    StockInfoDB.name.ilike(like),
                    StockInfoDB.ts_code.ilike(like),
                )
            )
        if industry:
            conditions.append(StockInfoDB.industry == industry)
        if market:
            conditions.append(StockInfoDB.market == market)
        if exchange:
            conditions.append(StockInfoDB.exchange == exchange)
        if is_hs:
            conditions.append(StockInfoDB.is_hs == is_hs)
        if list_status:
            conditions.append(StockInfoDB.list_status == list_status)
        if exclude_st is True:
            conditions.append(~StockInfoDB.name.ilike("%ST%"))
        elif exclude_st is False:
            conditions.append(StockInfoDB.name.ilike("%ST%"))

        if conditions:
            stmt = stmt.where(and_(*conditions))
            count_stmt = count_stmt.where(and_(*conditions))

        # min_total_mv：来自子查询列，需要 HAVING（聚合后）+ count_stmt 额外关联
        if min_total_mv is not None:
            stmt = stmt.having(latest_basic_sq.c.total_mv >= min_total_mv)
            count_stmt = (
                count_stmt
                .outerjoin(latest_basic_sq, StockInfoDB.symbol == latest_basic_sq.c.symbol)
                .where(latest_basic_sq.c.total_mv >= min_total_mv)
            )

        # ── 排序 + 分页 ───────────────────────────────────
        stmt = (
            stmt.order_by(StockInfoDB.symbol)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )

        rows = (await self._session.execute(stmt)).all()
        total = (await self._session.execute(count_stmt)).scalar_one()

        items = [
            StockPanelRow(
                symbol=r.symbol,
                ts_code=r.ts_code,
                name=r.name,
                area=r.area,
                industry=r.industry,
                market=r.market,
                exchange=r.exchange,
                list_date=_fmt_yyyymmdd(r.list_date),
                list_status=r.list_status,
                is_hs=r.is_hs,
                act_name=r.act_name,
                act_ent_type=r.act_ent_type,
                total_shares=r.total_shares,
                record_count=r.record_count or 0,
                kline_start=r.kline_start,
                kline_end=r.kline_end,
                latest_close=r.latest_close,
                total_mv=r.total_mv,
                pe_ttm=r.pe_ttm,
                profit_margin=(
                    round(r.profit_margin, 2)
                    if r.profit_margin is not None else None
                ),
            )
            for r in rows
        ]
        return items, int(total)

    # ── 批量反向查询池（从 PoolRepoImpl 平移过来）─────────────

    async def list_membership_by_symbols(
        self, symbols: list[str]
    ) -> dict[str, list[PoolMembershipVO]]:
        """按 symbols 批量查询池成员关系

        单次 SQL：
        SELECT m.symbol, p.id, p.name, p.pool_type
        FROM stock_pool_members m
        JOIN stock_pools p ON p.id = m.pool_id
        WHERE m.symbol IN (:symbols) AND p.is_archived = false
        ORDER BY p.is_default DESC, p.updated_at DESC

        返回 dict[symbol, list[PoolMembershipVO]]。
        未出现在 dict key 中的 symbol 表示未加入任何池。
        """
        if not symbols:
            return {}

        stmt = (
            select(
                StockPoolMemberDB.symbol,
                StockPoolDB.id,
                StockPoolDB.name,
                StockPoolDB.pool_type,
            )
            .join(StockPoolDB, StockPoolDB.id == StockPoolMemberDB.pool_id)
            .where(
                and_(
                    StockPoolMemberDB.symbol.in_(symbols),
                    StockPoolDB.is_archived == False,
                )
            )
            .order_by(
                StockPoolDB.is_default.desc(),
                StockPoolDB.updated_at.desc(),
            )
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        out: dict[str, list[PoolMembershipVO]] = {s: [] for s in symbols}
        for row in rows:
            out[row.symbol].append(
                PoolMembershipVO(
                    pool_id=row.id,
                    name=row.name,
                    pool_type=row.pool_type,
                )
            )
        return out


# ── Protocol 实现标注（运行时检查） ────────────────────────────
StockPanelComposeRepoImpl.__implements_protocol__ = StockPanelComposeRepository