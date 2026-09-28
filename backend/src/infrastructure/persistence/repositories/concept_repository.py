"""Concept 仓储实现

写侧方法只被概念采集任务使用；读侧方法实现 domain 的 ConceptRepository 协议。

配套设计文档：
  docs/dev/06gainian/02-infrastructure-design.md §3
  docs/dev/step2/02datamanage/04-概念数据adata同源改造方案.md §5.3
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Iterable, Optional

from sqlalchemy import and_, delete, func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entitys.concept.entity import Concept, ConceptSource, ConceptType
from domain.entitys.concept.repository import ConceptRepository
from domain.entitys.concept.vo import ConceptBriefVO, ConceptGroupedVO
from infrastructure.persistence.models.concept import (
    ConceptIndexTHDB,
    ConceptMemberDB,
    ConceptSnapshotDB,
    ConceptsDB,
)
from route.dto.request.concept import ConceptIndexTHBO, ConceptListBO, ConceptSnapshotBO

logger = logging.getLogger(__name__)

# asyncpg 单条语句最多 32767 个绑定参数
_INDEX_TH_CHUNK = 2000


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _chunks(items: list, size: int) -> Iterable[list]:
    for i in range(0, len(items), size):
        yield items[i:i + size]


class ConceptRepoImpl:
    """概念仓储实现"""

    def __init__(self, session: AsyncSession):
        self._session = session

    def _to_entity(self, row: ConceptsDB) -> Concept:
        return Concept(
            id=row.id,
            index_code=row.index_code,
            concept_code=row.concept_code,
            name=row.name,
            source=ConceptSource(row.source),
            concept_type=ConceptType(row.concept_type) if row.concept_type in ConceptType._value2member_map_ else ConceptType.OTHER,
            description=row.description,
            stock_count=row.stock_count,
            is_active=row.is_active,
            first_seen_at=row.first_seen_at,
            last_synced_at=row.last_synced_at,
        )

    # ═════════════════════════════════════════════════════════════════════
    #  写侧：概念清单
    # ═════════════════════════════════════════════════════════════════════

    async def upsert_concepts(self, bos: list[ConceptListBO]) -> dict[str, int]:
        """按 index_code 批量 upsert；只更新 name / concept_code / is_active，不碰 stock_count

        Returns: {index_code: concept_id}
        """
        if not bos:
            return {}
        values = [
            {"index_code": b.index_code, "concept_code": b.concept_code, "name": b.name,
             "source": ConceptSource.THS.value, "is_active": True, "first_seen_at": _now()}
            for b in bos
        ]
        stmt = pg_insert(ConceptsDB).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["index_code"],
            set_={
                "name": stmt.excluded.name,
                "concept_code": func.coalesce(stmt.excluded.concept_code, ConceptsDB.concept_code),
                "is_active": True,
            },
        ).returning(ConceptsDB.index_code, ConceptsDB.id)
        rows = (await self._session.execute(stmt)).all()
        await self._session.commit()
        return {r.index_code: r.id for r in rows}

    async def count_active(self) -> int:
        stmt = select(func.count()).select_from(ConceptsDB).where(ConceptsDB.is_active == True)  # noqa: E712
        return int((await self._session.execute(stmt)).scalar_one())

    async def deactivate_missing(self, index_codes: list[str]) -> int:
        """不在本次清单里的概念置为不活跃"""
        stmt = (
            update(ConceptsDB)
            .where(ConceptsDB.is_active == True, ConceptsDB.index_code.not_in(index_codes))  # noqa: E712
            .values(is_active=False)
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount or 0

    async def list_active_concepts(self) -> list[tuple[int, str, str]]:
        """活跃概念 [(id, index_code, name)]，按 index_code 排序"""
        stmt = (
            select(ConceptsDB.id, ConceptsDB.index_code, ConceptsDB.name)
            .where(ConceptsDB.is_active == True)  # noqa: E712
            .order_by(ConceptsDB.index_code)
        )
        return [(r.id, r.index_code, r.name) for r in (await self._session.execute(stmt)).all()]

    async def concept_id_map(self) -> dict[str, int]:
        """{index_code: concept_id}（含不活跃概念）"""
        stmt = select(ConceptsDB.index_code, ConceptsDB.id)
        return {r.index_code: r.id for r in (await self._session.execute(stmt)).all()}

    # ═════════════════════════════════════════════════════════════════════
    #  写侧：成分股 / 入选理由
    # ═════════════════════════════════════════════════════════════════════

    async def count_members(self, concept_id: int) -> int:
        stmt = select(func.count()).select_from(ConceptMemberDB).where(ConceptMemberDB.concept_id == concept_id)
        return int((await self._session.execute(stmt)).scalar_one())

    async def replace_members(self, concept_id: int, symbols: list[str]) -> tuple[int, int]:
        """用本次成分股替换概念的成员（集合差），保留已有关系的 reason

        同一事务内回填 concepts.stock_count / last_synced_at。
        Returns: (added, removed)
        """
        new_set = set(symbols)
        existing = set(
            (await self._session.execute(
                select(ConceptMemberDB.symbol).where(ConceptMemberDB.concept_id == concept_id)
            )).scalars().all()
        )
        to_remove = existing - new_set
        to_add = new_set - existing
        now = _now()

        if to_remove:
            await self._session.execute(
                delete(ConceptMemberDB).where(
                    ConceptMemberDB.concept_id == concept_id,
                    ConceptMemberDB.symbol.in_(to_remove),
                )
            )
        if to_add:
            rows = [
                {"symbol": s, "concept_id": concept_id, "source": ConceptSource.THS.value,
                 "joined_at": now, "synced_at": now}
                for s in sorted(to_add)
            ]
            for chunk in _chunks(rows, 5000):
                await self._session.execute(
                    pg_insert(ConceptMemberDB).values(chunk).on_conflict_do_nothing(
                        index_elements=["symbol", "concept_id"],
                    )
                )
        await self._session.execute(
            update(ConceptMemberDB)
            .where(ConceptMemberDB.concept_id == concept_id)
            .values(synced_at=now)
        )
        await self._session.execute(
            update(ConceptsDB)
            .where(ConceptsDB.id == concept_id)
            .values(stock_count=len(new_set), last_synced_at=now)
        )
        await self._session.commit()
        return len(to_add), len(to_remove)

    async def list_member_symbols(self, only_missing_reason: bool = False) -> list[str]:
        """有概念关系的股票；only_missing_reason=True 时只返回还有 reason 为空的股票"""
        stmt = select(ConceptMemberDB.symbol).distinct()
        if only_missing_reason:
            stmt = stmt.where(ConceptMemberDB.reason.is_(None))
        stmt = stmt.order_by(ConceptMemberDB.symbol)
        return list((await self._session.execute(stmt)).scalars().all())

    async def update_reasons(self, symbol: str, pairs: list[tuple[int, str]]) -> int:
        """只更新已存在关系的 reason，不插入新关系（成分股任务是关系唯一写入方）"""
        updated = 0
        for concept_id, reason in pairs:
            result = await self._session.execute(
                update(ConceptMemberDB)
                .where(ConceptMemberDB.symbol == symbol, ConceptMemberDB.concept_id == concept_id)
                .values(reason=reason)
            )
            updated += result.rowcount or 0
        await self._session.commit()
        return updated

    # ═════════════════════════════════════════════════════════════════════
    #  写侧：指数日 K / 快照
    # ═════════════════════════════════════════════════════════════════════

    async def get_max_trade_dates(self) -> dict[str, date]:
        stmt = select(ConceptIndexTHDB.index_code, func.max(ConceptIndexTHDB.trade_date)).group_by(
            ConceptIndexTHDB.index_code
        )
        return {code: d for code, d in (await self._session.execute(stmt)).all()}

    async def upsert_index_th(self, bos: list[ConceptIndexTHBO]) -> int:
        """按 (index_code, trade_date) 批量 upsert 概念指数日 K"""
        if not bos:
            return 0
        now = _now()
        written = 0
        values_all = [
            {
                "index_code": b.index_code,
                "concept_name": b.concept_name,
                "trade_date": b.trade_date,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
                "amount": b.amount,
                "change": b.change,
                "change_pct": b.change_pct,
                "captured_at": now,
            }
            for b in bos
        ]
        for values in _chunks(values_all, _INDEX_TH_CHUNK):
            stmt = pg_insert(ConceptIndexTHDB).values(values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["index_code", "trade_date"],
                set_={
                    "concept_name": stmt.excluded.concept_name,
                    "open": stmt.excluded.open,
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "volume": stmt.excluded.volume,
                    "amount": stmt.excluded.amount,
                    "change": stmt.excluded.change,
                    "change_pct": stmt.excluded.change_pct,
                    "captured_at": stmt.excluded.captured_at,
                },
            )
            result = await self._session.execute(stmt)
            written += result.rowcount or 0
        await self._session.commit()
        return written

    async def get_prev_closes(self, before: date) -> dict[str, float]:
        """每个概念 trade_date < before 的最近一个收盘价（快照任务的昨收）"""
        sql = text("""
            SELECT DISTINCT ON (index_code) index_code, close
            FROM concept_index_ths
            WHERE trade_date < :before
            ORDER BY index_code, trade_date DESC
        """)
        rows = (await self._session.execute(sql, {"before": before})).all()
        return {r.index_code: float(r.close) for r in rows}

    async def insert_snapshots(self, bos: list[ConceptSnapshotBO]) -> int:
        """一批快照一次写入（不覆盖历史）"""
        if not bos:
            return 0
        values = [
            {
                "index_code": b.index_code,
                "concept_name": b.concept_name,
                "trade_time": b.trade_time,
                "open_price": b.open_price,
                "high": b.high,
                "low": b.low,
                "price": b.price,
                "prev_close": b.prev_close,
                "pct_change": b.pct_change,
                "rank_current": b.rank_current,
                "rank_total": b.rank_total,
                "volume_wan": b.volume_wan,
                "turnover_yi": b.turnover_yi,
                "source": ConceptSource.THS.value,
                "captured_at": b.captured_at,
            }
            for b in bos
        ]
        for chunk in _chunks(values, 1000):
            await self._session.execute(pg_insert(ConceptSnapshotDB).values(chunk))
        await self._session.commit()
        return len(values)

    # ═════════════════════════════════════════════════════════════════════
    #  读侧
    # ═════════════════════════════════════════════════════════════════════

    async def get_concept_by_id(self, concept_id: int) -> Optional[Concept]:
        row = await self._session.get(ConceptsDB, concept_id)
        return self._to_entity(row) if row else None

    async def get_concept_by_name(self, name: str) -> Optional[Concept]:
        """同名时优先活跃概念"""
        stmt = (
            select(ConceptsDB)
            .where(ConceptsDB.name == name)
            .order_by(ConceptsDB.is_active.desc(), ConceptsDB.id)
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def list_members(self, concept_id: int) -> list[dict]:
        sql = text("""
            SELECT m.symbol, COALESCE(s.name, '') AS name, m.reason
            FROM stock_concept_members m
            LEFT JOIN stock_infos s ON s.symbol = m.symbol
            WHERE m.concept_id = :cid
            ORDER BY m.symbol
        """)
        rows = (await self._session.execute(sql, {"cid": concept_id})).mappings().all()
        return [dict(r) for r in rows]

    async def list_concepts_by_symbol(self, symbol: str) -> list[ConceptBriefVO]:
        return (await self.list_concepts_by_symbols([symbol])).get(symbol, [])

    async def list_concepts_by_symbols(
        self, symbols: list[str]
    ) -> dict[str, list[ConceptBriefVO]]:
        """批量反查：单次 SQL，避免 N+1"""
        if not symbols:
            return {}
        stmt = (
            select(
                ConceptMemberDB.symbol,
                ConceptsDB.id,
                ConceptsDB.name,
                ConceptsDB.source,
                ConceptsDB.concept_type,
            )
            .join(ConceptsDB, ConceptMemberDB.concept_id == ConceptsDB.id)
            .where(
                and_(
                    ConceptMemberDB.symbol.in_(symbols),
                    ConceptsDB.is_active == True,  # noqa: E712
                )
            )
        )
        rows = (await self._session.execute(stmt)).all()
        out: dict[str, list[ConceptBriefVO]] = {s: [] for s in symbols}
        for r in rows:
            out[r.symbol].append(
                ConceptBriefVO(
                    concept_id=r.id,
                    name=r.name,
                    source=r.source,
                    concept_type=r.concept_type or "other",
                )
            )
        return out

    async def list_concepts_by_symbol_grouped(
        self, symbol: str
    ) -> list[ConceptGroupedVO]:
        """单股票所属概念（含 concept_type / reason，用于详情抽屉「概念」Tab）"""
        stmt = (
            select(
                ConceptsDB.id,
                ConceptsDB.name,
                ConceptsDB.source,
                ConceptsDB.concept_type,
                ConceptsDB.description,
                ConceptMemberDB.reason,
            )
            .join(ConceptMemberDB, ConceptMemberDB.concept_id == ConceptsDB.id)
            .where(
                and_(
                    ConceptMemberDB.symbol == symbol,
                    ConceptsDB.is_active == True,  # noqa: E712
                )
            )
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            ConceptGroupedVO(
                concept_id=r.id,
                name=r.name,
                source=r.source,
                concept_type=r.concept_type,
                description=r.description,
                reason=r.reason,
            )
            for r in rows
        ]

    async def list_concepts(
        self,
        q: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Concept], int]:
        stmt = select(ConceptsDB)
        count_stmt = select(func.count()).select_from(ConceptsDB)
        if q:
            cond = ConceptsDB.name.ilike(f"%{q}%") | (ConceptsDB.index_code == q)
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if is_active is not None:
            stmt = stmt.where(ConceptsDB.is_active == is_active)
            count_stmt = count_stmt.where(ConceptsDB.is_active == is_active)

        total = (await self._session.execute(count_stmt)).scalar_one()
        stmt = (
            stmt.order_by(ConceptsDB.stock_count.desc(), ConceptsDB.name)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_entity(r) for r in rows], int(total)

    async def count_concepts(self, is_active: Optional[bool] = None) -> int:
        stmt = select(func.count()).select_from(ConceptsDB)
        if is_active is not None:
            stmt = stmt.where(ConceptsDB.is_active == is_active)
        return int((await self._session.execute(stmt)).scalar_one())

    async def get_last_synced_at(self) -> Optional[datetime]:
        stmt = select(func.max(ConceptsDB.last_synced_at))
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_latest_snapshot(self, concept_name: str) -> Optional[dict]:
        return (await self.list_snapshots_for_names([concept_name])).get(concept_name)

    async def list_snapshots_for_names(self, names: list[str]) -> dict[str, dict]:
        """批量取多个概念的最新一条快照（窗口函数，单 SQL）"""
        if not names:
            return {}
        sql = text("""
            WITH ranked AS (
                SELECT
                    index_code, concept_name, trade_time, open_price, high, low, price,
                    prev_close, pct_change, rank_current, rank_total,
                    up_count, down_count, volume_wan, net_inflow_yi, turnover_yi,
                    captured_at,
                    ROW_NUMBER() OVER (PARTITION BY concept_name ORDER BY captured_at DESC) AS rn
                FROM concept_snapshots
                WHERE concept_name = ANY(:names)
            )
            SELECT * FROM ranked WHERE rn = 1
        """)
        rows = (await self._session.execute(sql, {"names": names})).mappings().all()
        return {r["concept_name"]: _snapshot_dict(r) for r in rows}

    async def list_index_th(
        self,
        concept_name: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 500,
    ) -> list[dict]:
        """指定概念指数日 K，按 trade_date DESC"""
        stmt = select(ConceptIndexTHDB).where(ConceptIndexTHDB.concept_name == concept_name)
        if start_date:
            stmt = stmt.where(ConceptIndexTHDB.trade_date >= start_date)
        if end_date:
            stmt = stmt.where(ConceptIndexTHDB.trade_date <= end_date)
        stmt = stmt.order_by(ConceptIndexTHDB.trade_date.desc()).limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            {
                "trade_date": r.trade_date,
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
                "amount": r.amount,
                "change": r.change,
                "change_pct": r.change_pct,
            }
            for r in rows
        ]


def _snapshot_dict(r) -> dict:
    pct = r["pct_change"]
    return {
        "index_code": r["index_code"],
        "concept_name": r["concept_name"],
        "trade_time": r["trade_time"],
        "price": r["price"],
        "prev_close": r["prev_close"],
        "pct_change": pct,
        "rank_current": r["rank_current"],
        "rank_total": r["rank_total"],
        "rank_label": (
            f"{r['rank_current']}/{r['rank_total']}" if r["rank_current"] is not None else ""
        ),
        "up_count": r["up_count"],
        "down_count": r["down_count"],
        "up_down_label": (
            f"{r['up_count']}/{r['down_count']}" if r["up_count"] is not None else ""
        ),
        "volume_wan": r["volume_wan"],
        "net_inflow_yi": r["net_inflow_yi"],
        "turnover_yi": r["turnover_yi"],
        "captured_at": r["captured_at"],
        "color": (
            "flat" if pct is None else "up" if pct > 0 else "down" if pct < 0 else "flat"
        ),
    }


ConceptRepoImpl.__implements_protocol__ = ConceptRepository
