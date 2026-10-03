"""概念大盘应用服务（业务模块：concept-board/）

业务范围：
- query_board：概念大盘列表（分页 + 实时行情补齐 + 排序）
- query_board_members：概念成分股（分页 + 池信息 + 实时涨幅）
- get_kline：概念指数日 K 线（concept_index_ths）+ 实时快照

注：通用概念查询（详情/反查/抽屉 Tab）见 concept_service.py（共享层）

依赖通过构造注入（DDD.md §4）：
- repo:        概念仓储
- realtime:    实时行情端口（可选，实时不可用时降级为最近收盘）
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from application.port.realtime_query_port import RealtimeQueryPort
from domain.entitys.concept.repository import ConceptRepository
from route.dto.request.concept_board import (
    ConceptBoardQueryRequest,
    ConceptMembersQueryRequest,
)
from route.dto.response.concept_board import CONCEPT_BOARD_TYPE_LABELS

logger = logging.getLogger(__name__)


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
    }


def _kline_color(pct: Optional[float]) -> str:
    if pct is None or pct == 0:
        return "flat"
    return "up" if pct > 0 else "down"


class ConceptBoardService:
    """概念大盘应用服务（依赖注入）"""

    def __init__(
        self,
        *,
        repo: ConceptRepository,
        realtime: Optional[RealtimeQueryPort] = None,
    ):
        self._repo = repo
        self._realtime = realtime

    # ── 概念大盘列表 ─────────────────────────────────────────

    async def query_board(self, req: ConceptBoardQueryRequest) -> dict:
        """概念大盘：分页 + 实时行情补齐 + 排序

        性能：1 DB 查询（分页）+ 1 实时接口批量调用（page_size≤500 时一次性 query_many）
        """
        rows, total = await self._repo.list_board_rows(
            type_filter=req.type_filter,
            sort_by=req.sort_by,
            order=req.order,
            page=req.page,
            page_size=req.page_size,
        )

        index_codes = [r.index_code for r in rows]
        names = {r.index_code: r.name for r in rows}
        if self._realtime and index_codes:
            quotes = await self._realtime.query_many(
                "concept_minute",
                [{"index_code": c} for c in index_codes],
            )
            quote_map = {
                r.index_code: _to_quote(r.index_code, names.get(r.index_code, ""), res)
                for r, res in zip(rows, quotes)
                if getattr(res, "data", None)
            }
        else:
            quote_map = {}

        items = []
        for r in rows:
            q = quote_map.get(r.index_code, {})
            items.append({
                "concept_id": r.concept_id,
                "index_code": r.index_code,
                "name": r.name,
                "source": r.source,
                "concept_type": r.concept_type,
                "concept_type_label": CONCEPT_BOARD_TYPE_LABELS.get(
                    r.concept_type, r.concept_type,
                ),
                "stock_count": r.stock_count,
                "description": r.description,
                "price": q.get("price"),
                "prev_close": q.get("prev_close"),
                "change": q.get("change"),
                "pct_change": q.get("pct_change"),
                "color": q.get("color", "flat"),
                "trade_time": q.get("trade_time"),
                "captured_at": q.get("captured_at"),
                "stale": q.get("stale", False),
            })

        if req.sort_by == "pct_change":
            items.sort(
                key=lambda x: (
                    x["pct_change"] is None,
                    -(x["pct_change"] or 0) if req.order == "desc"
                    else (x["pct_change"] or 0),
                )
            )

        pages = (total + req.page_size - 1) // req.page_size if total > 0 else 0
        return {
            "items": items, "total": total,
            "page": req.page, "page_size": req.page_size, "pages": pages,
        }

    # ── 概念成分股 ───────────────────────────────────────────

    async def query_board_members(self, req: ConceptMembersQueryRequest) -> dict:
        """概念成分股：分页 + 池信息 + 实时涨幅（仅前 50 只调实时）"""
        rows, total = await self._repo.list_members_by_concept(
            concept_id=req.concept_id,
            sort_by=req.sort_by,
            order=req.order,
            page=req.page,
            page_size=req.page_size,
        )
        symbols = [r["symbol"] for r in rows]
        pool_map: dict[str, list[dict]] = {}
        if req.with_pools and symbols:
            pool_map = await self._repo.list_membership_by_symbols(symbols)

        realtime_map: dict[str, dict] = {}
        if self._realtime and symbols and len(symbols) <= 50:
            results = await self._realtime.query_many(
                "stock_minute_kline",
                [{"symbol": s, "interval": "1d"} for s in symbols],
            )
            for s, res in zip(symbols, results):
                if res and getattr(res, "data", None) and not getattr(res, "stale", False):
                    d = res.data
                    pct = d.get("pct_change")
                    realtime_map[s] = {
                        "pct_change": pct,
                        "color": (
                            "up" if (pct or 0) > 0
                            else "down" if (pct or 0) < 0
                            else "flat"
                        ),
                    }

        items = [
            {
                "symbol": r["symbol"],
                "name": r.get("name"),
                "industry": r.get("industry"),
                "market": r.get("market"),
                "latest_close": r.get("latest_close"),
                "total_mv": r.get("total_mv"),
                "pe_ttm": r.get("pe_ttm"),
                "pct_change": realtime_map.get(r["symbol"], {}).get("pct_change"),
                "color": realtime_map.get(r["symbol"], {}).get("color", "flat"),
                "pools": pool_map.get(r["symbol"], []),
            }
            for r in rows
        ]
        if req.sort_by == "pct_change":
            items.sort(
                key=lambda x: (
                    x["pct_change"] is None,
                    -(x["pct_change"] or 0) if req.order == "desc"
                    else (x["pct_change"] or 0),
                )
            )
        pages = (total + req.page_size - 1) // req.page_size if total > 0 else 0
        return {
            "items": items, "total": total,
            "page": req.page, "page_size": req.page_size, "pages": pages,
        }

    # ── 概念日 K + 实时 ──────────────────────────────────────

    async def get_kline(
        self,
        index_code: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        days: int = 250,
    ) -> dict:
        """概念指数日 K 线 + 实时快照 + meta

        返回：
        {
          "kline": [{date, open, high, low, close, volume, amount, change_pct, color}, ...] 升序,
          "realtime": {price, prev_close, change, pct_change, color, trade_time, captured_at, stale} | None,
          "meta": {index_code, name, concept_type, stock_count},
          "data_range": {start, end, bars_count}
        }
        """
        # 1) K 线（升序）
        bars = await self._repo.list_concept_kline(
            index_code=index_code,
            start_date=start_date, end_date=end_date, limit=days,
        )
        # 加 color 字段
        for b in bars:
            b["color"] = _kline_color(b.get("change_pct"))

        # 2) 实时
        realtime = None
        if self._realtime and index_code:
            results = await self._realtime.query_many(
                "concept_minute", [{"index_code": index_code}],
            )
            if results and getattr(results[0], "data", None):
                names = await self._repo.get_names([index_code])
                realtime = _to_quote(
                    index_code, names.get(index_code, ""), results[0],
                )

        # 3) meta
        entity = await self._repo.get_concept_by_index_code(index_code)
        meta = None
        if entity is not None:
            meta = {
                "concept_id": entity.id,
                "index_code": entity.index_code,
                "name": entity.name,
                "concept_type": (
                    entity.concept_type.value
                    if hasattr(entity.concept_type, "value")
                    else entity.concept_type
                ),
                "stock_count": entity.stock_count,
                "description": entity.description,
                "source": (
                    entity.source.value
                    if hasattr(entity.source, "value")
                    else entity.source
                ),
            }
            # 实时不可用时,降级用最近收盘
            if realtime is None:
                latest = await self._repo.get_latest_closes([index_code])
                snap = latest.get(index_code)
                if snap:
                    realtime = {
                        "index_code": index_code,
                        "concept_name": entity.name,
                        "price": snap.get("close"),
                        "prev_close": None,
                        "change": snap.get("change"),
                        "pct_change": snap.get("change_pct"),
                        "color": _kline_color(snap.get("change_pct")),
                        "trade_time": (
                            snap["trade_date"].isoformat()
                            if hasattr(snap.get("trade_date"), "isoformat")
                            else str(snap.get("trade_date"))
                        ),
                        "captured_at": None,
                        "stale": True,
                    }

        # 4) data_range
        if bars:
            data_range = {
                "start": bars[0]["date"],
                "end": bars[-1]["date"],
                "bars_count": len(bars),
            }
        else:
            data_range = {"start": None, "end": None, "bars_count": 0}

        return {
            "kline": bars,
            "realtime": realtime,
            "meta": meta,
            "data_range": data_range,
        }
