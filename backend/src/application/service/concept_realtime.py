"""概念实时行情读取（concept_service / concept_board_service 共用）

经 DataGateway 以 QUERY 策略查 concept_minute（15 秒缓存 + 单飞由数据层负责）；
数据源失败或无数据时降级为库里最近一条日 K 收盘，标 stale=true —— 降级属于业务决策，放在应用层。
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any, Optional

from application.port.data import DataGatewayPort
from application.port.data.base import CallPolicy, DataResult, InvalidParams
from application.port.data.concept import ConceptMinuteBO, ConceptMinutePort
from domain.entitys.concept.repository import ConceptRepository

logger = logging.getLogger(__name__)


@dataclass
class ConceptMinuteVO:
    """data 为分时 BO 的字段字典（降级时 points 为空）；fetched_at 为 ISO 字符串"""

    data: Optional[dict[str, Any]]
    cached: bool = False
    stale: bool = False
    fetched_at: Optional[str] = None
    latency_ms: int = 0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_result(cls, res: DataResult) -> "ConceptMinuteVO":
        bo: ConceptMinuteBO = res.items[0]
        return cls(
            data=bo.model_dump(),
            cached=res.cached,
            fetched_at=res.fetched_at.isoformat() if res.fetched_at else None,
            latency_ms=res.latency_ms,
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
    def __init__(self, gateway: DataGatewayPort, repo: ConceptRepository) -> None:
        self._gateway = gateway
        self._repo = repo

    async def minutes(self, codes: list[str]) -> dict[str, ConceptMinuteVO]:
        """批量查询；拿不到实时也没有收盘可降级的概念，返回 data=None + error"""
        codes = list(dict.fromkeys(c for c in codes if c))
        if not codes:
            return {}
        results = await self._gateway.fetch_many(
            ConceptMinutePort, [{"index_code": c} for c in codes], policy=CallPolicy.QUERY,
        )
        out: dict[str, ConceptMinuteVO] = {}
        failed: dict[str, str] = {}
        for code, res in zip(codes, results):
            if isinstance(res, DataResult) and res.items:
                out[code] = ConceptMinuteVO.from_result(res)
                continue
            if isinstance(res, InvalidParams):
                logger.error("concept_minute 参数错误 %s: %r", code, res)
            elif isinstance(res, Exception):
                logger.warning("concept_minute(%s) 请求失败: %r", code, res)
            failed[code] = repr(res) if isinstance(res, Exception) else "无数据"
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
