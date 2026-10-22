"""股票信息仓储实现

实现 domain/stock_info/repository.py 中的 StockInfoRepository 接口。
面板组合查询（4 表 JOIN）已迁移至 infrastructure/repositories/panel_compose_repository.py。
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select, func, or_, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.market.domain.entities.stock_info.entity import StockInfo
from contexts.market.domain.entities.stock_info.repository import StockInfoRepository
from contexts.market.infrastructure.persistence.models.stock_basic import StockBasicDB
from contexts.market.infrastructure.persistence.models.tech_kline import TechKlineDailyDB


class StockRepoImpl:
    """股票信息仓储实现（双 session：raw 主表 + attr 业务关联）

    实现 domain/stock_info/repository.py 中的 StockInfoRepository 接口。
    - raw_session:  StockBasicDB / TechKlineDailyDB
    - attr_session: 未来扩展（如果 stock 业务关联用户自选股/角色）
    """

    def __init__(self, raw_session: AsyncSession, attr_session: AsyncSession | None = None):
        self._raw = raw_session
        self._attr = attr_session
        self._session = raw_session  # 向后兼容

    # ── ORM ↔ Entity 转换 ───────────────────────────────────

    def _to_entity(self, row: StockBasicDB) -> StockInfo:
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
            "act_name": stock.act_name,
            "act_ent_type": stock.act_ent_type,
        }

    # ── CRUD ──────────────────────────────────────────────

    async def save(self, stock: StockInfo) -> StockInfo:
        row = StockBasicDB(**self._to_row(stock))
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        stock.id = row.id
        return stock

    async def find_by_symbol(self, symbol: str) -> Optional[StockInfo]:
        stmt = select(StockBasicDB).where(StockBasicDB.symbol == symbol)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def find_all(
        self,
        industry: Optional[str] = None,
        market: Optional[str] = None,
    ) -> list[StockInfo]:
        stmt = select(StockBasicDB)
        if industry:
            stmt = stmt.where(StockBasicDB.industry == industry)
        if market:
            stmt = stmt.where(StockBasicDB.market == market)
        stmt = stmt.order_by(StockBasicDB.symbol)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_entity(row) for row in rows]

    async def upsert(self, stock: StockInfo) -> StockInfo:
        row_dict = self._to_row(stock)
        stmt = (
            pg_insert(StockBasicDB)
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
        excluded = pg_insert(StockBasicDB).excluded
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
            "act_name":     excluded.act_name,
            "act_ent_type": excluded.act_ent_type,
        }

        total_inserted = 0
        for i in range(0, len(stocks), BATCH_SIZE):
            batch = stocks[i : i + BATCH_SIZE]
            rows = [self._to_row(s) for s in batch]
            stmt = (
                pg_insert(StockBasicDB)
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
        stmt = select(StockBasicDB).where(StockBasicDB.symbol == symbol)
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
                StockBasicDB.symbol,
                StockBasicDB.name,
                StockBasicDB.industry,
                StockBasicDB.market,
                func.count(TechKlineDailyDB.id).label("record_count"),
                func.min(TechKlineDailyDB.date).label("kline_start"),
                func.max(TechKlineDailyDB.date).label("kline_end"),
            )
            .outerjoin(TechKlineDailyDB, StockBasicDB.symbol == TechKlineDailyDB.symbol)
            .group_by(StockBasicDB.id)
            .order_by(StockBasicDB.symbol)
        )
        if industry:
            stmt = stmt.where(StockBasicDB.industry == industry)
        if market:
            stmt = stmt.where(StockBasicDB.market == market)

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
        stmt = select(StockBasicDB)
        count_stmt = select(func.count()).select_from(StockBasicDB)

        conditions = []
        if q:
            like = f"%{q}%"
            conditions.append(
                or_(
                    StockBasicDB.symbol.ilike(like),
                    StockBasicDB.name.ilike(like),
                    StockBasicDB.ts_code.ilike(like),
                )
            )
        if industry:
            conditions.append(StockBasicDB.industry == industry)
        if market:
            conditions.append(StockBasicDB.market == market)
        if exchange:
            conditions.append(StockBasicDB.exchange == exchange)
        if is_hs:
            conditions.append(StockBasicDB.is_hs == is_hs)
        if list_status:  # 空字符串表示"全部"
            conditions.append(StockBasicDB.list_status == list_status)

        if conditions:
            stmt = stmt.where(and_(*conditions))
            count_stmt = count_stmt.where(and_(*conditions))

        stmt = stmt.order_by(StockBasicDB.symbol).limit(page_size).offset((page - 1) * page_size)

        rows = (await self._session.execute(stmt)).scalars().all()
        total = (await self._session.execute(count_stmt)).scalar_one()
        return [self._to_entity(r) for r in rows], int(total)

    async def distinct_meta(self) -> dict[str, list[str]]:
        """获取 industry / market / exchange 的去重值"""

        async def _distinct_values(col) -> list[str]:
            stmt = select(col).distinct().where(col.isnot(None)).order_by(col)
            rows = (await self._session.execute(stmt)).scalars().all()
            return [v for v in rows if v]

        return {
            "industries": await _distinct_values(StockBasicDB.industry),
            "markets":    await _distinct_values(StockBasicDB.market),
            "exchanges":  await _distinct_values(StockBasicDB.exchange),
        }


StockRepoImpl.__implements_protocol__ = StockInfoRepository
