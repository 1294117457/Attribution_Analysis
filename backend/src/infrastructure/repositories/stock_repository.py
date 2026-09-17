"""股票信息仓储实现"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select, func, or_, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.stock_info.entity import StockInfo
from domain.stock_info.repository import StockInfoRepository
from infrastructure.database.models.stock_info import StockInfoDB
from infrastructure.database.models.tech_kline import TechKlineDailyDB
from infrastructure.database.models.fin_daily_basic import FinDailyBasicDB


class StockRepoImpl:
    """股票信息仓储实现

    实现 domain/stock_info/repository.py 中的 StockInfoRepository 接口。
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    # ── ORM ↔ Entity 转换 ───────────────────────────────────

    def _to_entity(self, row: StockInfoDB) -> StockInfo:
        """ORM → Entity"""
        return StockInfo.create(
            id=row.id,
            symbol=row.symbol,
            name=row.name or "",
            industry=row.industry,
            market=row.market,
            area=row.area,
            exchange=row.exchange,
            list_date=row.list_date,
            delist_date=row.delist_date,
            list_status=row.list_status,
            is_hs=row.is_hs,
            total_shares=row.total_shares,
            act_name=row.act_name,
            act_ent_type=row.act_ent_type,
            ts_code=row.ts_code,
        )

    @staticmethod
    def _to_row(stock: StockInfo) -> dict:
        """Entity → ORM"""
        return {
            "symbol": stock.symbol,
            "ts_code": stock.ts_code,
            "name": stock.name,
            "area": stock.area,
            "industry": stock.industry.name if stock.industry else None,
            "market": stock.market.name if stock.market else None,
            "exchange": stock.exchange,
            "list_date": stock.list_date,
            "delist_date": stock.delist_date,
            "list_status": stock.list_status or "L",
            "is_hs": stock.is_hs or "N",
            "total_shares": stock.total_shares,
            "act_name": stock.act_name,
            "act_ent_type": stock.act_ent_type,
        }

    # ── CRUD ──────────────────────────────────────────────

    async def save(self, stock: StockInfo) -> StockInfo:
        row = StockInfoDB(**self._to_row(stock))
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        stock.id = row.id
        return stock

    async def find_by_symbol(self, symbol: str) -> Optional[StockInfo]:
        stmt = select(StockInfoDB).where(StockInfoDB.symbol == symbol)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def find_all(
        self,
        industry: Optional[str] = None,
        market: Optional[str] = None,
    ) -> list[StockInfo]:
        stmt = select(StockInfoDB)
        if industry:
            stmt = stmt.where(StockInfoDB.industry == industry)
        if market:
            stmt = stmt.where(StockInfoDB.market == market)
        stmt = stmt.order_by(StockInfoDB.symbol)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_entity(row) for row in rows]

    async def upsert(self, stock: StockInfo) -> StockInfo:
        row_dict = self._to_row(stock)
        stmt = (
            pg_insert(StockInfoDB)
            .values(**row_dict)
            .on_conflict_do_update(
                index_elements=["symbol"],
                set_=row_dict,
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()
        return stock

    async def bulk_upsert(self, stocks: list[StockInfo]) -> int:
        """批量 upsert，返回成功条数

        PostgreSQL 单次 INSERT 最多 32767 个参数，按 BATCH_SIZE 分批写入。
        """
        if not stocks:
            return 0

        BATCH_SIZE = 1000  # 12 列 × 1000 行 = 12000 参数，安全余量
        excluded = pg_insert(StockInfoDB).excluded
        upsert_set = {
            "ts_code":      excluded.ts_code,
            "name":         excluded.name,
            "area":         excluded.area,
            "industry":     excluded.industry,
            "market":       excluded.market,
            "exchange":     excluded.exchange,
            "list_date":    excluded.list_date,
            "delist_date":  excluded.delist_date,
            "list_status":  excluded.list_status,
            "is_hs":        excluded.is_hs,
            "total_shares": excluded.total_shares,
            "act_name":     excluded.act_name,
            "act_ent_type": excluded.act_ent_type,
        }

        total_inserted = 0
        for i in range(0, len(stocks), BATCH_SIZE):
            batch = stocks[i : i + BATCH_SIZE]
            rows = [self._to_row(s) for s in batch]
            stmt = (
                pg_insert(StockInfoDB)
                .values(rows)
                .on_conflict_do_update(
                    index_elements=["symbol"],
                    set_=upsert_set,
                )
            )
            result = await self._session.execute(stmt)
            total_inserted += result.rowcount or len(batch)

        await self._session.commit()
        return total_inserted

    async def delete(self, symbol: str) -> bool:
        stmt = select(StockInfoDB).where(StockInfoDB.symbol == symbol)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row:
            await self._session.delete(row)
            await self._session.commit()
            return True
        return False

    # ── 联表查询：股票 + K线统计 ──────────────────────────

    async def list_with_kline_stats(
        self,
        industry: Optional[str] = None,
        market: Optional[str] = None,
    ) -> list[dict]:
        stmt = (
            select(
                StockInfoDB.symbol,
                StockInfoDB.name,
                StockInfoDB.industry,
                StockInfoDB.market,
                func.count(TechKlineDailyDB.id).label("record_count"),
                func.min(TechKlineDailyDB.date).label("kline_start"),
                func.max(TechKlineDailyDB.date).label("kline_end"),
            )
            .outerjoin(TechKlineDailyDB, StockInfoDB.symbol == TechKlineDailyDB.symbol)
            .group_by(StockInfoDB.id)
            .order_by(StockInfoDB.symbol)
        )
        if industry:
            stmt = stmt.where(StockInfoDB.industry == industry)
        if market:
            stmt = stmt.where(StockInfoDB.market == market)

        result = await self._session.execute(stmt)
        rows = result.all()
        return [
            {
                "symbol": r.symbol,
                "name": r.name,
                "industry": r.industry,
                "market": r.market,
                "record_count": r.record_count,
                "kline_start": r.kline_start,
                "kline_end": r.kline_end,
            }
            for r in rows
        ]

    async def list_paginated(
        self,
        q: Optional[str] = None,
        industry: Optional[str] = None,
        market: Optional[str] = None,
        exchange: Optional[str] = None,
        is_hs: Optional[str] = None,
        list_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[StockInfo], int]:
        """分页查询（不含 K线统计）"""
        stmt = select(StockInfoDB)
        count_stmt = select(func.count()).select_from(StockInfoDB)

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
        if list_status:  # 空字符串表示"全部"
            conditions.append(StockInfoDB.list_status == list_status)

        if conditions:
            stmt = stmt.where(and_(*conditions))
            count_stmt = count_stmt.where(and_(*conditions))

        stmt = stmt.order_by(StockInfoDB.symbol).limit(page_size).offset((page - 1) * page_size)

        rows = (await self._session.execute(stmt)).scalars().all()
        total = (await self._session.execute(count_stmt)).scalar_one()
        return [self._to_entity(r) for r in rows], int(total)

    async def list_with_kline_stats_paginated(
        self,
        q: Optional[str] = None,
        industry: Optional[str] = None,
        market: Optional[str] = None,
        exchange: Optional[str] = None,
        is_hs: Optional[str] = None,
        list_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """分页 + 多维筛选 + K线统计 + 最新估值（前端主列表用）"""

        # 子查询：每只股票在 fin_daily_basics 中最新 trade_date
        latest_date_sq = (
            select(
                FinDailyBasicDB.symbol,
                func.max(FinDailyBasicDB.trade_date).label("max_date"),
            )
            .group_by(FinDailyBasicDB.symbol)
            .subquery("latest_date")
        )

        # 子查询：用 max_date 取对应行的 close / total_mv / pe_ttm
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
            )
            .outerjoin(TechKlineDailyDB, StockInfoDB.symbol == TechKlineDailyDB.symbol)
            .outerjoin(latest_basic_sq, StockInfoDB.symbol == latest_basic_sq.c.symbol)
            .group_by(StockInfoDB.id, latest_basic_sq.c.latest_close, latest_basic_sq.c.total_mv, latest_basic_sq.c.pe_ttm)
        )
        count_stmt = select(func.count()).select_from(StockInfoDB)

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

        if conditions:
            stmt = stmt.where(and_(*conditions))
            count_stmt = count_stmt.where(and_(*conditions))

        stmt = (
            stmt.order_by(StockInfoDB.symbol)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )

        rows = (await self._session.execute(stmt)).all()
        total = (await self._session.execute(count_stmt)).scalar_one()

        items = [
            {
                "symbol":        r.symbol,
                "ts_code":       r.ts_code,
                "name":          r.name,
                "area":          r.area,
                "industry":      r.industry,
                "market":        r.market,
                "exchange":      r.exchange,
                "list_date":     _fmt_yyyymmdd(r.list_date),
                "list_status":   r.list_status,
                "is_hs":         r.is_hs,
                "act_name":      r.act_name,
                "act_ent_type":  r.act_ent_type,
                "total_shares":  r.total_shares,
                "record_count":  r.record_count,
                "kline_start":   r.kline_start,
                "kline_end":     r.kline_end,
                "latest_close":  r.latest_close,
                "total_mv":      r.total_mv,
                "pe_ttm":        r.pe_ttm,
            }
            for r in rows
        ]
        return items, int(total)

    async def distinct_meta(self) -> dict[str, list[str]]:
        """获取 industry / market / exchange 的去重值"""

        async def _distinct_values(col) -> list[str]:
            stmt = select(col).distinct().where(col.isnot(None)).order_by(col)
            rows = (await self._session.execute(stmt)).scalars().all()
            return [v for v in rows if v]

        return {
            "industries": await _distinct_values(StockInfoDB.industry),
            "markets":    await _distinct_values(StockInfoDB.market),
            "exchanges":  await _distinct_values(StockInfoDB.exchange),
        }


def _fmt_yyyymmdd(d) -> Optional[str]:
    if d is None:
        return None
    return d.strftime("%Y%m%d")


StockRepoImpl.__implements_protocol__ = StockInfoRepository
