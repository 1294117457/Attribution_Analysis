"""概念应用服务

写入只走采集任务（infrastructure/adapter/scheduler/collect/concept.py），本服务只负责查询与实时反查。

DDD 改造（2026-10-03）：不再持有 AsyncSession / 不再 import `infrastructure.persistence.*`；
实时行情通过 RealtimeQueryPort 注入。

配套设计文档：
  docs/dev/06gainian/03-application-and-route-design.md §2.1
  docs/dev/step2/02datamanage/04-概念数据adata同源改造方案.md §5.5
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from route.dto.response.concept import (
    ConceptDetailVO,
    ConceptItemVO,
    ConceptLiveVO,
    ConceptMemberVO,
    ConceptQueryRequest,
    ConceptTabContentVO,
    ConceptTabSectionVO,
    CONCEPT_TYPE_LABELS,
    CONCEPT_TYPE_ORDER,
)
from application.port.page import Page
from application.port.collector_port import ConceptFetcher
from application.port.realtime_query_port import RealtimeQueryPort
from domain.entitys.concept.entity import Concept, ConceptNotFoundError
from domain.entitys.concept.repository import ConceptRepository
from domain.entitys.concept.vo import CONCEPT_TYPE_PRIORITY, ConceptBriefVO

logger = logging.getLogger(__name__)


def _enum_value(v) -> str:
    return v.value if hasattr(v, "value") else v


def _item_fields(c: Concept) -> dict:
    return {
        "concept_id": c.id,
        "index_code": c.index_code,
        "name": c.name,
        "source": _enum_value(c.source),
        "concept_type": _enum_value(c.concept_type),
        "stock_count": c.stock_count,
        "description": c.description,
        "is_active": c.is_active,
        "last_synced_at": c.last_synced_at,
        "first_seen_at": c.first_seen_at,
    }


class ConceptAppService:
    """概念应用服务

    职责：
    - 查询：列表 / 详情（成分股读库）/ 反查（供 panel 调用）
    - 实时反查：按股票调同花顺拿所属概念与入选理由（不入库）
    """

    def __init__(
        self,
        *,
        repo: ConceptRepository,
        fetcher: ConceptFetcher,
        realtime: Optional[RealtimeQueryPort] = None,
    ):
        self._repo = repo
        self._fetcher = fetcher
        self._realtime = realtime

    # ── 查询 ─────────────────────────────────────────

    async def query_concepts(self, req: ConceptQueryRequest) -> Page[ConceptItemVO]:
        """分页查询概念列表"""
        concepts, total = await self._repo.list_concepts(
            q=req.q,
            is_active=req.is_active,
            page=req.page,
            page_size=req.page_size,
        )
        items = [ConceptItemVO(**_item_fields(c)) for c in concepts]
        return Page[ConceptItemVO].from_list(items, total, req.page, req.page_size)

    async def get_concept_detail(self, name: str) -> ConceptDetailVO:
        """概念详情（成分股来自库，由概念成分股任务维护）"""
        concept = await self._repo.get_concept_by_name(name)
        if not concept:
            raise ConceptNotFoundError(name=name)
        members = [ConceptMemberVO(**m) for m in await self._repo.list_members(concept.id)]
        return ConceptDetailVO(**_item_fields(concept), members=members)

    # ── 反向查询（供 panel 复用）──────────────────────

    async def list_for_symbol(self, symbol: str) -> list[ConceptBriefVO]:
        """单只股票所属的所有活跃概念"""
        return await self._repo.list_concepts_by_symbol(symbol)

    async def list_for_symbols(self, symbols: list[str]) -> dict[str, list[ConceptBriefVO]]:
        """批量反向查询（避免 N+1）"""
        return await self._repo.list_concepts_by_symbols(symbols)

    # ── 实时行情（实时接口 concept_minute）──────────────

    async def get_quotes(
        self, index_codes: list[str], names: Optional[dict[str, str]] = None,
    ) -> dict[str, dict]:
        """批量概念实时行情 {index_code: quote}；字段兼容前端 ConceptSnapshot"""
        codes = list(dict.fromkeys(c for c in index_codes if c))
        if not codes:
            return {}
        if names is None:
            names = await self._repo.get_names(codes)
        if self._realtime is None:
            return {}
        results = await self._realtime.query_many(
            "concept_minute", [{"index_code": c} for c in codes],
        )
        return {
            code: _to_quote(code, names.get(code, ""), res)
            for code, res in zip(codes, results)
            if res.data
        }

    # ── 实时反查 ─────────────────────────────────────

    def fetch_concepts_by_stock(self, symbol: str) -> list[ConceptLiveVO]:
        """按股票代码实时反查所属概念（同花顺 F10，带入选理由，约 0.5s/只，不入库）"""
        bos = self._fetcher.fetch_concepts_by_stock(symbol)
        return [
            ConceptLiveVO(concept_code=bo.index_code, name=bo.name, source="ths", reason=bo.reason)
            for bo in bos
        ]

    # ── 详情抽屉「概念」Tab 专用 ──────────────────────

    async def get_tab_content_for_symbol(
        self,
        symbol: str,
        stock_name: Optional[str] = None,
    ) -> ConceptTabContentVO:
        """详情抽屉「概念」Tab：库中概念按 concept_type 分组，附实时行情与入选理由"""
        grouped_vos = await self._repo.list_concepts_by_symbol_grouped(symbol)
        quotes = await self.get_quotes(
            [v.index_code for v in grouped_vos],
            names={v.index_code: v.name for v in grouped_vos if v.index_code},
        )

        bucket: dict[str, list] = {t: [] for t in CONCEPT_TYPE_ORDER}
        for vo in grouped_vos:
            bucket.setdefault(vo.concept_type, []).append({
                "concept_id": vo.concept_id,
                "index_code": vo.index_code,
                "name": vo.name,
                "source": vo.source,
                "concept_type": vo.concept_type,
                "description": vo.description,
                "reason": vo.reason,
                "snapshot": quotes.get(vo.index_code),
            })

        sections = _build_sections(bucket)
        return ConceptTabContentVO(
            symbol=symbol,
            stock_name=stock_name or "",
            sections=sections,
            total_count=sum(len(s.concepts) for s in sections),
        )

    async def get_tab_content_with_live(
        self,
        symbol: str,
        stock_name: Optional[str] = None,
    ) -> ConceptTabContentVO:
        """详情抽屉「概念」Tab：库中概念 + 同花顺实时反查合并

        - 按 (name, source) 去重，共有概念用实时 reason 覆盖库中 reason
        - 排序：实时优先 → type 优先级 → name
        - 实时反查失败时降级为仅库中数据
        """
        grouped_vos = await self._repo.list_concepts_by_symbol_grouped(symbol)

        live_vos: list[ConceptLiveVO] = []
        try:
            live_vos = self.fetch_concepts_by_stock(symbol)
        except Exception as e:
            logger.warning("实时反查 %s 失败，降级为仅 DB: %s", symbol, e)

        code_names = {v.index_code: v.name for v in grouped_vos if v.index_code}
        code_names.update({v.concept_code: v.name for v in live_vos if v.concept_code})
        quotes = await self.get_quotes(list(code_names), names=code_names)

        db_index: dict[tuple[str, str], dict] = {
            (v.name, v.source): {
                "concept_id": v.concept_id,
                "index_code": v.index_code,
                "name": v.name,
                "source": v.source,
                "concept_type": v.concept_type,
                "description": v.description,
                "concept_code": None,
                "is_realtime": False,
                "reason": v.reason,
                "snapshot": quotes.get(v.index_code),
            }
            for v in grouped_vos
        }
        live_index: dict[tuple[str, str], ConceptLiveVO] = {(v.name, v.source): v for v in live_vos}

        merged_rows: list[dict] = []
        for key in db_index.keys() | live_index.keys():
            db_row = db_index.get(key)
            live_row = live_index.get(key)
            if db_row and live_row:
                merged_rows.append({
                    **db_row,
                    "concept_code": live_row.concept_code,
                    "is_realtime": True,
                    "reason": live_row.reason or db_row["reason"],
                })
            elif db_row:
                merged_rows.append(db_row)
            else:
                merged_rows.append({
                    "concept_id": None,
                    "index_code": live_row.concept_code,
                    "concept_code": live_row.concept_code,
                    "name": live_row.name,
                    "source": live_row.source,
                    "concept_type": "other",
                    "description": None,
                    "is_realtime": True,
                    "reason": live_row.reason,
                    "snapshot": quotes.get(live_row.concept_code),
                })

        merged_rows.sort(
            key=lambda r: (
                0 if r["is_realtime"] else 1,
                CONCEPT_TYPE_PRIORITY.get(r["concept_type"], 99),
                r["name"],
            ),
        )

        bucket: dict[str, list[dict]] = {t: [] for t in CONCEPT_TYPE_ORDER}
        for row in merged_rows:
            bucket.setdefault(row["concept_type"], []).append(row)

        return ConceptTabContentVO(
            symbol=symbol,
            stock_name=stock_name or "",
            sections=_build_sections(bucket),
            total_count=len(merged_rows),
            is_merged=True,
            last_merged_at=datetime.now(timezone.utc),
        )


def _build_sections(bucket: dict[str, list[dict]]) -> list[ConceptTabSectionVO]:
    """各分组内按当日涨跌幅降序，无行情的排最后"""

    def key(r: dict):
        pct = (r.get("snapshot") or {}).get("pct_change")
        return (pct is None, -(pct or 0), r["name"])

    return [
        ConceptTabSectionVO(
            type=t,
            type_label=CONCEPT_TYPE_LABELS.get(t, t),
            concepts=sorted(bucket[t], key=key),
        )
        for t in CONCEPT_TYPE_ORDER
        if bucket.get(t)
    ]


def _to_quote(index_code: str, name: str, res: object) -> dict:
    d = (getattr(res, "data", None) or {})
    pct = d.get("change_pct")
    return {
        "index_code": index_code,
        "concept_name": name,
        "price": d.get("price"),
        "prev_close": d.get("pre_close"),
        "change": d.get("change"),
        "pct_change": pct,
        "color": "flat" if not pct else ("up" if pct > 0 else "down"),
        "trade_time": d.get("trade_time"),
        "captured_at": getattr(res, "fetched_at", None),
        "stale": getattr(res, "stale", False),
        "rank_label": "",
        "up_down_label": "",
    }