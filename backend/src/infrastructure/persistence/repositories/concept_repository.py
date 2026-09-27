"""Concept 仓储实现

配套设计文档：
  docs/dev/06gainian/02-infrastructure-design.md §3
  docs/dev/09concept/02-class-design.md §5
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Optional

from sqlalchemy import and_, delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.concept.entity import Concept, ConceptMember, ConceptSource
from domain.concept.repository import ConceptRepository
from domain.concept.schemas import ConceptIndexTHBO, ConceptSnapshotBO
from domain.concept.value_objects import ConceptBriefVO, ConceptGroupedVO
from infrastructure.persistence.models.concept import (
    ConceptIndexTHDB,
    ConceptMemberDB,
    ConceptSnapshotDB,
    ConceptsDB,
)

logger = logging.getLogger(__name__)


def _src(val) -> str:
    """统一提取 source 字段的字符串值"""
    return val.value if hasattr(val, "value") else str(val)


def _ctype(val) -> str:
    """统一提取 concept_type 字段的字符串值"""
    return val.value if hasattr(val, "value") else str(val)


class ConceptRepoImpl:
    """概念仓储实现"""

    def __init__(self, session: AsyncSession):
        self._session = session

    # ── ORM ↔ Entity 转换 ─────────────────────────────────

    def _to_entity(self, row: ConceptsDB) -> Concept:
        return Concept(
            id=row.id,
            name=row.name,
            source=ConceptSource(row.source),
            concept_type=row.concept_type,
            description=row.description,
            stock_count=row.stock_count,
            is_active=row.is_active,
            first_seen_at=row.first_seen_at,
            last_synced_at=row.last_synced_at,
        )

    def _to_brief_vo(
        self, concept_id: int, name: str, source: str
    ) -> ConceptBriefVO:
        return ConceptBriefVO(
            concept_id=concept_id,
            name=name,
            source=source,
        )

    # ── 写入 ─────────────────────────────────────────────

    async def upsert_concept(self, concept: Concept) -> Concept:
        row_dict = {
            "name": concept.name,
            "source": _src(concept.source),
            "concept_type": _ctype(concept.concept_type),
            "description": concept.description,
            "stock_count": concept.stock_count,
            "is_active": concept.is_active,
            "last_synced_at": concept.last_synced_at,
        }
        stmt = (
            pg_insert(ConceptsDB)
            .values(**row_dict)
            .on_conflict_do_update(
                index_elements=["name", "source"],
                set_={
                    **row_dict,
                    "is_active": True,  # 重新上线时激活
                },
            )
            .returning(ConceptsDB.id)
        )
        result = await self._session.execute(stmt)
        concept.id = result.scalar_one()
        await self._session.commit()
        return concept

    async def upsert_members(
        self,
        concept_id: int,
        members: list[ConceptMember],
    ) -> int:
        """全量覆盖语义：DELETE + INSERT"""
        # 1. DELETE 旧成员
        await self._session.execute(
            delete(ConceptMemberDB).where(
                ConceptMemberDB.concept_id == concept_id
            )
        )
        # 2. INSERT 新成员
        if not members:
            await self._session.commit()
            return 0

        rows = [
            {
                "symbol": m.symbol,
                "concept_id": concept_id,
                "joined_at": m.joined_at,
                "source": _src(m.source),
            }
            for m in members
        ]
        self._session.add_all([ConceptMemberDB(**r) for r in rows])
        await self._session.commit()
        return len(rows)

    # ── 单条读取 ────────────────────────────────────────

    async def get_concept_by_id(self, concept_id: int) -> Optional[Concept]:
        stmt = select(ConceptsDB).where(ConceptsDB.id == concept_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def get_concept_by_name(
        self, name: str, source: str = "em"
    ) -> Optional[Concept]:
        stmt = select(ConceptsDB).where(
            and_(
                ConceptsDB.name == name,
                ConceptsDB.source == source,
            )
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_entity(row) if row else None

    # ── 反向查询 ────────────────────────────────────────

    async def list_concepts_by_symbol(
        self, symbol: str
    ) -> list[ConceptBriefVO]:
        stmt = (
            select(
                ConceptsDB.id,
                ConceptsDB.name,
                ConceptsDB.source,
            )
            .join(ConceptMemberDB, ConceptMemberDB.concept_id == ConceptsDB.id)
            .where(
                and_(
                    ConceptMemberDB.symbol == symbol,
                    ConceptsDB.is_active == True,
                )
            )
        )
        rows = (await self._session.execute(stmt)).all()
        return [self._to_brief_vo(r.id, r.name, r.source) for r in rows]

    async def list_concepts_by_symbols(
        self, symbols: list[str]
    ) -> dict[str, list[ConceptBriefVO]]:
        """批量反查：单次 SQL，避免 N+1。

        返回 dict[symbol, list[ConceptBriefVO]]，
        未在结果中的 symbol 表示无活跃概念（不会自动补 key）。
        08concept 增量：SELECT 中追加 concept_type 列，使 VO.concept_type 有值。
        """
        if not symbols:
            return {}

        stmt = (
            select(
                ConceptMemberDB.symbol,
                ConceptsDB.id,
                ConceptsDB.name,
                ConceptsDB.source,
                ConceptsDB.concept_type,  # 08concept: 用于主概念列排序
            )
            .join(ConceptsDB, ConceptMemberDB.concept_id == ConceptsDB.id)
            .where(
                and_(
                    ConceptMemberDB.symbol.in_(symbols),
                    ConceptsDB.is_active == True,
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
        """单股票所属概念（含 concept_type / description，用于详情抽屉「概念」Tab）"""
        stmt = (
            select(
                ConceptsDB.id,
                ConceptsDB.name,
                ConceptsDB.source,
                ConceptsDB.concept_type,
                ConceptsDB.description,
            )
            .join(ConceptMemberDB, ConceptMemberDB.concept_id == ConceptsDB.id)
            .where(
                and_(
                    ConceptMemberDB.symbol == symbol,
                    ConceptsDB.is_active == True,
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
            )
            for r in rows
        ]

    # ── 列表 / 统计 ───────────────────────────────────

    async def list_concepts(
        self,
        q: Optional[str] = None,
        source: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Concept], int]:
        stmt = select(ConceptsDB)
        count_stmt = select(func.count()).select_from(ConceptsDB)

        conditions = []
        if q:
            stmt = stmt.where(ConceptsDB.name.ilike(f"%{q}%"))
            count_stmt = count_stmt.where(ConceptsDB.name.ilike(f"%{q}%"))
        if source:
            stmt = stmt.where(ConceptsDB.source == source)
            count_stmt = count_stmt.where(ConceptsDB.source == source)
        if is_active is not None:
            stmt = stmt.where(ConceptsDB.is_active == is_active)
            count_stmt = count_stmt.where(ConceptsDB.is_active == is_active)

        total = (await self._session.execute(count_stmt)).scalar_one()
        stmt = (
            stmt.order_by(ConceptsDB.name)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_entity(r) for r in rows], int(total)

    async def count_concepts(
        self,
        source: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        stmt = select(func.count()).select_from(ConceptsDB)
        if source:
            stmt = stmt.where(ConceptsDB.source == source)
        if is_active is not None:
            stmt = stmt.where(ConceptsDB.is_active == is_active)
        return int((await self._session.execute(stmt)).scalar_one())

    async def get_last_synced_at(self, source: str = "em") -> Optional[datetime]:
        stmt = (
            select(func.max(ConceptsDB.last_synced_at))
            .where(ConceptsDB.source == source)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    # ═════════════════════════════════════════════════════════════════════
    #  09concept 新增方法（M:N 反查累加 + 行情快照 + 概念指数 K 线）
    # ═════════════════════════════════════════════════════════════════════

    async def upsert_single_member(
        self,
        symbol: str,
        concept_id: int,
        source: ConceptSource,
    ) -> bool:
        """单条插入 M:N（ON CONFLICT NOOP，09concept 新增）

        用于 adata 反查模式：一只只股票枚举写入多个 concept。
        与 upsert_members（全量覆盖）语义不同：
        - upsert_members：DELETE 旧 + INSERT 新
        - upsert_single_member：ON CONFLICT DO NOTHING（累加）

        Returns: True 新插入；False 已存在（NOOP）
        """
        stmt = pg_insert(ConceptMemberDB).values(
            symbol=symbol,
            concept_id=concept_id,
            source=_src(source),
            joined_at=datetime.now(),
        ).on_conflict_do_nothing(
            index_elements=["symbol", "concept_id"],
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount > 0

    async def get_concept_id_by_name(
        self,
        name: str,
        source: ConceptSource = ConceptSource.THS,
    ) -> Optional[int]:
        """根据 (name, source) 查询概念 id（09concept 新增）

        用于 adata 反查后回填 concept_id：
        - 命中 → 返回已有 id
        - 未命中 → 返回 None（应用层应先 upsert_concept）
        """
        stmt = select(ConceptsDB.id).where(
            and_(
                ConceptsDB.name == name,
                ConceptsDB.source == _src(source),
            )
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return int(row) if row is not None else None

    async def list_active_concept_names(self, source: str = "ths") -> list[str]:
        """列出所有活跃概念名（09concept 新增，用于 snapshot/index 全量采集）

        Returns: 按 name 排序的概念名列表
        """
        stmt = (
            select(ConceptsDB.name)
            .where(ConceptsDB.is_active == True, ConceptsDB.source == source)
            .order_by(ConceptsDB.name)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [str(r) for r in rows]

    async def upsert_snapshot(self, bo: ConceptSnapshotBO) -> int:
        """插入新快照（不覆盖历史，09concept 新增）

        Returns: 1
        """
        db = ConceptSnapshotDB(
            concept_name=bo.concept_name,
            open_price=bo.open_price,
            prev_close=bo.prev_close,
            low=bo.low,
            high=bo.high,
            volume_wan=bo.volume_wan,
            pct_change=bo.to_pct_change(),
            rank_current=bo.rank_current,
            rank_total=bo.rank_total,
            up_count=bo.up_count,
            down_count=bo.down_count,
            net_inflow_yi=bo.net_inflow_yi,
            turnover_yi=bo.turnover_yi,
            source=_src(bo.source),
            captured_at=bo.captured_at,
        )
        self._session.add(db)
        await self._session.commit()
        return 1

    async def upsert_index_th(self, rows: list[ConceptIndexTHBO]) -> int:
        """批量 upsert 概念指数日 K（按 (name, date) 冲突更新，09concept 新增）

        Returns: 实际写入条数
        """
        if not rows:
            return 0
        values = [
            {
                "concept_name": r.concept_name,
                "trade_date": r.trade_date,
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
                "amount": r.amount,
                "captured_at": r.captured_at,
            }
            for r in rows
        ]
        stmt = pg_insert(ConceptIndexTHDB).values(values).on_conflict_do_update(
            index_elements=["concept_name", "trade_date"],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "amount": stmt.excluded.amount,
                "captured_at": stmt.excluded.captured_at,
            },
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount or 0

    async def list_latest_snapshot(
        self,
        concept_name: str,
    ) -> Optional[dict]:
        """取指定概念最新一条快照（09concept 新增，用于前端涨染色）

        返回 dict 而非 VO（VO 在 application 层构造，避免循环依赖）
        """
        stmt = (
            select(ConceptSnapshotDB)
            .where(ConceptSnapshotDB.concept_name == concept_name)
            .order_by(ConceptSnapshotDB.captured_at.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return {
            "concept_name": row.concept_name,
            "pct_change": row.pct_change,
            "rank_current": row.rank_current,
            "rank_total": row.rank_total,
            "rank_label": f"{row.rank_current}/{row.rank_total}" if row.rank_current else "",
            "up_count": row.up_count,
            "down_count": row.down_count,
            "up_down_label": f"{row.up_count}/{row.down_count}" if row.up_count is not None else "",
            "net_inflow_yi": row.net_inflow_yi,
            "turnover_yi": row.turnover_yi,
            "captured_at": row.captured_at,
            "color": (
                "up" if row.pct_change > 0 else
                "down" if row.pct_change < 0 else
                "flat"
            ),
        }

    async def list_snapshots_for_names(
        self,
        names: list[str],
    ) -> dict[str, dict]:
        """批量取多个概念的"最新一条"快照（09concept 新增，避免 N+1）

        用窗口函数 ROW_NUMBER() OVER (PARTITION BY concept_name ORDER BY captured_at DESC)
        单 SQL 拿到 N 个概念的快照。

        Returns: {concept_name: snapshot_dict, ...}
        """
        if not names:
            return {}
        from sqlalchemy import text as sql_text
        sql = sql_text("""
            WITH ranked AS (
                SELECT
                    concept_name, open_price, prev_close, low, high, volume_wan,
                    pct_change, rank_current, rank_total,
                    up_count, down_count, net_inflow_yi, turnover_yi,
                    captured_at,
                    ROW_NUMBER() OVER (PARTITION BY concept_name ORDER BY captured_at DESC) AS rn
                FROM concept_snapshots
                WHERE concept_name = ANY(:names)
            )
            SELECT * FROM ranked WHERE rn = 1
        """)
        rows = (await self._session.execute(sql, {"names": names})).mappings().all()
        out: dict[str, dict] = {}
        for r in rows:
            pct = float(r["pct_change"] or 0.0)
            out[r["concept_name"]] = {
                "concept_name": r["concept_name"],
                "pct_change": pct,
                "rank_current": r["rank_current"],
                "rank_total": r["rank_total"],
                "rank_label": (
                    f"{r['rank_current']}/{r['rank_total']}"
                    if r["rank_current"] is not None else ""
                ),
                "up_count": r["up_count"],
                "down_count": r["down_count"],
                "up_down_label": (
                    f"{r['up_count']}/{r['down_count']}"
                    if r["up_count"] is not None else ""
                ),
                "net_inflow_yi": r["net_inflow_yi"],
                "turnover_yi": r["turnover_yi"],
                "captured_at": r["captured_at"],
                "color": "up" if pct > 0 else ("down" if pct < 0 else "flat"),
            }
        return out

    async def list_index_th(
        self,
        concept_name: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 500,
    ) -> list[dict]:
        """取指定概念指数日 K（09concept 新增）

        Returns: [{trade_date, open, high, low, close, volume, amount}, ...]
        按 trade_date DESC 排序（最新在前）
        """
        stmt = (
            select(ConceptIndexTHDB)
            .where(ConceptIndexTHDB.concept_name == concept_name)
        )
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
            }
            for r in rows
        ]


# ── Protocol 实现标注 ─────────────────────────────────
ConceptRepoImpl.__implements_protocol__ = ConceptRepository
