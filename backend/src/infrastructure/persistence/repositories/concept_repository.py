"""Concept 仓储实现

写侧方法只被概念采集任务使用；读侧方法实现 domain 的 ConceptRepository 协议。

配套设计文档：
  docs/dev/06gainian/02-infrastructure-design.md §3
  docs/dev/step2/02datamanage/04-概念数据adata同源改造方案.md §5.3
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from dataclasses import dataclass
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
    ConceptsDB,
)
from infrastructure.persistence.models.pool import StockPoolDB, StockPoolMemberDB
from infrastructure.persistence.models.stock_info import StockInfoDB
from infrastructure.persistence.models.fin_daily_basic import FinDailyBasicDB
from route.dto.request.concept import ConceptIndexTHBO, ConceptListBO

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

    # ═════════════════════════════════════════════════════════════════════
    #  写侧：成分股
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

    # ═════════════════════════════════════════════════════════════════════
    #  写侧：指数日 K
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

    # ═════════════════════════════════════════════════════════════════════
    #  读侧
    # ═════════════════════════════════════════════════════════════════════

    async def get_latest_closes(self, index_codes: list[str]) -> dict[str, dict]:
        """每个概念最近一条日 K（实时行情失败时的降级数据）"""
        if not index_codes:
            return {}
        sql = text("""
            SELECT DISTINCT ON (t.index_code)
                t.index_code, COALESCE(c.name, t.concept_name) AS concept_name,
                t.trade_date, t.close, t.change, t.change_pct
            FROM concept_index_ths t
            LEFT JOIN concepts c ON c.index_code = t.index_code
            WHERE t.index_code = ANY(:codes)
            ORDER BY t.index_code, t.trade_date DESC
        """)
        rows = (await self._session.execute(sql, {"codes": index_codes})).mappings().all()
        return {r["index_code"]: dict(r) for r in rows}

    async def get_names(self, index_codes: list[str]) -> dict[str, str]:
        if not index_codes:
            return {}
        stmt = select(ConceptsDB.index_code, ConceptsDB.name).where(ConceptsDB.index_code.in_(index_codes))
        return {r.index_code: r.name for r in (await self._session.execute(stmt)).all()}

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
                ConceptsDB.index_code,
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
                index_code=r.index_code,
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


ConceptRepoImpl.__implements_protocol__ = ConceptRepository


# ═══════════════════════════════════════════════════════════════════════════════
#  概念大盘 v2（01 概念大盘页 · 纯追加，文件末尾）
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class _ConceptBoardRow:
    """概念大盘行（仓储私有 VO，不进 domain/vo/）

    用 dataclass 而非 ORM row 是因为实时字段（price / pct_change 等）
    由调用方补齐；这里只承载 DB 字段。
    """
    concept_id: int
    index_code: str
    name: str
    source: str
    concept_type: str
    description: Optional[str]
    stock_count: int
    is_active: bool


async def _list_board_rows_impl(
    self,
    type_filter: Optional[str] = None,
    sort_by: str = "pct_change",
    order: str = "desc",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[_ConceptBoardRow], int]:
    """按 type 筛选 + 排序 + 分页

    排序映射：
    - pct_change：实时字段，DB 没有；用 stock_count 兜底排序，
      service 端补行情后做内存重排
    - stock_count：stock_count DESC/ASC
    - name：name ASC/DESC
    """
    stmt = select(
        ConceptsDB.id,
        ConceptsDB.index_code,
        ConceptsDB.name,
        ConceptsDB.source,
        ConceptsDB.concept_type,
        ConceptsDB.description,
        ConceptsDB.stock_count,
        ConceptsDB.is_active,
    ).where(ConceptsDB.is_active == True)  # noqa: E712
    if type_filter and type_filter != "all":
        stmt = stmt.where(ConceptsDB.concept_type == type_filter)

    sort_col_map = {
        "pct_change": ConceptsDB.stock_count,
        "stock_count": ConceptsDB.stock_count,
        "name": ConceptsDB.name,
    }
    sort_col = sort_col_map.get(sort_by, ConceptsDB.stock_count)
    stmt = stmt.order_by(sort_col.desc() if order == "desc" else sort_col.asc())

    total = await self._session.scalar(
        select(func.count()).select_from(stmt.subquery())
    )
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await self._session.execute(stmt)
    rows = result.all()

    return [
        _ConceptBoardRow(
            concept_id=r.id,
            index_code=r.index_code,
            name=r.name,
            source=r.source.value if hasattr(r.source, "value") else r.source,
            concept_type=(
                r.concept_type.value
                if hasattr(r.concept_type, "value")
                else r.concept_type
            ),
            description=r.description,
            stock_count=r.stock_count,
            is_active=r.is_active,
        )
        for r in rows
    ], int(total or 0)


async def _list_members_by_concept_impl(
    self,
    concept_id: int,
    sort_by: str = "pct_change",
    order: str = "desc",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict], int]:
    """单概念成分股：stock_concept_members ⨝ stock_infos ⨝ fin_daily_basics 最新一行

    返回 dict 列表（路由层组装为 ConceptMemberItemVO）。
    """
    # 1) 子查询：每只股票 fin_daily_basics 最新一行
    latest_fdb = (
        select(
            FinDailyBasicDB.symbol,
            func.max(FinDailyBasicDB.trade_date).label("max_date"),
        )
        .group_by(FinDailyBasicDB.symbol)
        .subquery()
    )

    # 2) 主查询
    stmt = (
        select(
            StockInfoDB.symbol,
            StockInfoDB.name,
            StockInfoDB.industry,
            StockInfoDB.market,
            FinDailyBasicDB.close.label("latest_close"),
            FinDailyBasicDB.total_mv,
            FinDailyBasicDB.pe_ttm,
        )
        .select_from(ConceptMemberDB)
        .join(StockInfoDB, ConceptMemberDB.symbol == StockInfoDB.symbol)
        .outerjoin(latest_fdb, latest_fdb.c.symbol == StockInfoDB.symbol)
        .outerjoin(
            FinDailyBasicDB,
            and_(
                FinDailyBasicDB.symbol == latest_fdb.c.symbol,
                FinDailyBasicDB.trade_date == latest_fdb.c.max_date,
            ),
        )
        .where(ConceptMemberDB.concept_id == concept_id)
    )

    # 3) 排序（pct_change 用 latest_close 兜底）
    sort_col_map = {
        "pct_change": FinDailyBasicDB.close,
        "latest_close": FinDailyBasicDB.close,
        "total_mv": FinDailyBasicDB.total_mv,
        "name": StockInfoDB.name,
    }
    sort_col = sort_col_map.get(sort_by, FinDailyBasicDB.close)
    stmt = stmt.order_by(
        sort_col.desc().nulls_last() if order == "desc"
        else sort_col.asc().nulls_first()
    )

    # 4) 分页 + 返回 dict
    total = await self._session.scalar(
        select(func.count()).select_from(stmt.subquery())
    )
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await self._session.execute(stmt)
    rows = result.mappings().all()
    return [dict(r) for r in rows], int(total or 0)


async def _list_membership_by_symbols_impl(
    self, symbols: list[str]
) -> dict[str, list[dict]]:
    """批量查询股票所属池（避免 N+1）—— 用于概念成分股页 with_pools=True

    返回 dict[symbol, [{pool_id, name, pool_type, joined_at}, ...]]
    joined_at 用 StockPoolMemberDB.added_at（在结果 dict 内重命名）。
    """
    if not symbols:
        return {}
    stmt = (
        select(
            StockPoolMemberDB.symbol,
            StockPoolMemberDB.pool_id,
            StockPoolDB.name.label("pool_name"),
            StockPoolDB.pool_type,
            StockPoolMemberDB.added_at,
        )
        .join(StockPoolDB, StockPoolMemberDB.pool_id == StockPoolDB.id)
        .where(
            and_(
                StockPoolMemberDB.symbol.in_(symbols),
                StockPoolDB.is_archived == False,  # noqa: E712
            )
        )
    )
    rows = (await self._session.execute(stmt)).mappings().all()
    out: dict[str, list[dict]] = {s: [] for s in symbols}
    for r in rows:
        d = dict(r)
        # 字段重命名：added_at -> joined_at（与 PoolMembershipVO 一致）
        d["joined_at"] = d.pop("added_at")
        d["name"] = d.pop("pool_name")
        out[d.pop("symbol")].append(d)
    return out


# 挂载到 ConceptRepoImpl（动态方法注入，**不修改原类**）
ConceptRepoImpl.list_board_rows = _list_board_rows_impl
ConceptRepoImpl.list_members_by_concept = _list_members_by_concept_impl
ConceptRepoImpl.list_membership_by_symbols = _list_membership_by_symbols_impl


# ═══════════════════════════════════════════════════════════════════════════════
#  概念 K 线（concept-board 用）
# ═══════════════════════════════════════════════════════════════════════════════


async def _get_concept_by_index_code_impl(
    self, index_code: str
) -> Optional[Concept]:
    stmt = select(ConceptsDB).where(ConceptsDB.index_code == index_code)
    row = (await self._session.execute(stmt)).scalar_one_or_none()
    return self._to_entity(row) if row else None


async def _list_concept_kline_impl(
    self,
    index_code: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 250,
) -> list[dict]:
    """概念指数日 K（concept_index_ths），按日期升序

    返回 [{date(YYYY-MM-DD), open, high, low, close, volume, amount, change_pct}, ...]
    """
    from infrastructure.persistence.models.concept import ConceptIndexTHDB

    stmt = select(
        ConceptIndexTHDB.trade_date,
        ConceptIndexTHDB.open,
        ConceptIndexTHDB.high,
        ConceptIndexTHDB.low,
        ConceptIndexTHDB.close,
        ConceptIndexTHDB.volume,
        ConceptIndexTHDB.amount,
        ConceptIndexTHDB.change_pct,
    ).where(ConceptIndexTHDB.index_code == index_code)
    if start_date is not None:
        stmt = stmt.where(ConceptIndexTHDB.trade_date >= start_date)
    if end_date is not None:
        stmt = stmt.where(ConceptIndexTHDB.trade_date <= end_date)
    stmt = stmt.order_by(ConceptIndexTHDB.trade_date.desc()).limit(limit)
    rows = (await self._session.execute(stmt)).all()
    # 反转成升序
    out: list[dict] = []
    for r in reversed(rows):
        out.append({
            "date": r.trade_date.isoformat() if hasattr(r.trade_date, "isoformat") else str(r.trade_date),
            "open": r.open, "high": r.high, "low": r.low, "close": r.close,
            "volume": r.volume, "amount": r.amount,
            "change_pct": r.change_pct,
        })
    return out


ConceptRepoImpl.get_concept_by_index_code = _get_concept_by_index_code_impl
ConceptRepoImpl.list_concept_kline = _list_concept_kline_impl
