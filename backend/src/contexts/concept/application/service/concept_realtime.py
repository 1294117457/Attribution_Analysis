"""概念实时行情读取（step7 简化：直接调 fetcher）"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any, Optional

from contexts.collect.infrastructure.fetcher.fundamental.ConceptMinuteAdataFetcher import (
    ConceptMinuteAdataFetcher,
)
from contexts.collect.infrastructure.fetcher.fundamental.ConceptSnapshotAdataFetcher import (
    ConceptSnapshotAdataFetcher,
)
from contexts.collect.infrastructure.connect.adata_client import get_adata_client
from contexts.concept.domain.repository import ConceptRepository

logger = logging.getLogger(__name__)


@dataclass
class ConceptMinuteVO:
    data: Optional[dict[str, Any]]
    cached: bool = False
    stale: bool = False
    fetched_at: Optional[str] = None
    latency_ms: int = 0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_minute(cls, item: dict, fetched_at: str) -> "ConceptMinuteVO":
        return cls(
            data=item,
            fetched_at=fetched_at,
        )

    @classmethod
    def from_close(cls, index_code: str, row: dict) -> "ConceptMinuteVO":
        close, change = row["close"], row.get("change")
        trade_date = row.get("trade_date")
        day = str(trade_date) if trade_date else None
        return cls(
            data={
                "index_code": index_code,
                "trade_date": day,
                "pre_close": round(close - change, 4) if change is not None else None,
                "price": close,
                "change": change,
                "change_pct": row.get("change_pct"),
                "trade_time": day,
                "points": [],
            },
            stale=True,
        )


class ConceptRealtimeReader:
    def __init__(
        self,
        repo: ConceptRepository,
        minute_fetcher: Optional[ConceptMinuteAdataFetcher] = None,
        snapshot_fetcher: Optional[ConceptSnapshotAdataFetcher] = None,
    ) -> None:
        self._repo = repo
        self._minute = minute_fetcher
        self._snapshot = snapshot_fetcher

    async def minutes(self, codes: list[str]) -> dict[str, ConceptMinuteVO]:
        """批量查询；拿不到实时也没有收盘可降级的概念，返回 data=None + error"""
        codes = list(dict.fromkeys(c for c in codes if c))
        if not codes:
            return {}
        out: dict[str, ConceptMinuteVO] = {}
        failed: dict[str, str] = {}
        for code in codes:
            try:
                if self._minute is None:
                    out[code] = ConceptMinuteVO(data=None, error="concept minute fetcher 未配置")
                    continue
                items = await self._minute.fetch(index_code=code)
                if items:
                    out[code] = ConceptMinuteVO.from_minute(
                        items[0],
                        fetched_at=datetime.now().isoformat(),
                    )
                else:
                    failed[code] = "无数据"
            except Exception as e:
                logger.warning("concept_minute(%s) 请求失败: %r", code, e)
                failed[code] = repr(e)
        if failed:
            try:
                closes = await self._repo.get_latest_closes(list(failed))
            except Exception as e:
                logger.warning("概念行情降级查询失败: %r", e)
                closes = {}
            for code, error in failed.items():
                row = closes.get(code)
                if row and row.get("close") is not None:
                    out[code] = ConceptMinuteVO.from_close(code, row)
                else:
                    out[code] = ConceptMinuteVO(data=None, error=error)
        return out

    async def minute(self, index_code: str) -> ConceptMinuteVO:
        return (await self.minutes([index_code]))[index_code]


__all__ = ["ConceptMinuteVO", "ConceptRealtimeReader"]
