"""StockBasicTushareFetcher：股票基本信息（Tushare stock_basic）—— step7 重构版

替代旧 StockBasicTushareAdapter(StockBasicPort, AdapterBase, TushareAdapterBase)
"""
from __future__ import annotations

import logging
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from collectors.base import BaseFetcher
from core.tushare_utils import (
    parse_list_date,
    rows,
    text,
)
from core.tushare_client import get_tushare_client
from collectors.schemas import StockInfoBO

logger = logging.getLogger(__name__)


class ListStatus(StrEnum):
    LISTED = "L"
    DELISTED = "D"
    PAUSED = "P"


class StockBasicParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    list_status: ListStatus = ListStatus.LISTED

_STOCK_BASIC_FIELDS = (
    "ts_code,symbol,name,area,industry,market,exchange,list_date,delist_date,"
    "list_status,is_hs,act_name,act_ent_type"
)
_EXCHANGES = ("SSE", "SZSE", "BSE")


class StockBasicTushareFetcher(BaseFetcher):
    """股票基本信息 fetcher（Tushare stock_basic）"""

    fetcher_type = "stock_basic_tushare"
    source = "tushare"
    label = "股票基本信息（Tushare）"
    description = "Tushare stock_basic 接口"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        p = StockBasicParams.model_validate(params or {"list_status": "L"})
        out: list[StockInfoBO] = []
        errors: list[str] = []
        for ex in _EXCHANGES:
            try:
                df = await self._c.query(
                    "stock_basic", exchange=ex, list_status=p.list_status.value,
                    fields=_STOCK_BASIC_FIELDS,
                )
            except Exception as e:
                logger.warning("拉取 %s stock_basic 失败: %r", ex, e)
                errors.append(f"{ex}: {e}")
                continue
            for r in rows(df):
                symbol = text(r, "symbol")
                if not symbol:
                    continue
                try:
                    out.append(StockInfoBO(
                        symbol=symbol.zfill(6),
                        ts_code=text(r, "ts_code"),
                        name=text(r, "name") or "",
                        area=text(r, "area"),
                        industry=text(r, "industry"),
                        market=text(r, "market"),
                        exchange=text(r, "exchange"),
                        list_date=parse_list_date(r.get("list_date")),
                        delist_date=parse_list_date(r.get("delist_date")),
                        list_status=text(r, "list_status") or "L",
                        is_hs=text(r, "is_hs") or "N",
                        act_name=text(r, "act_name"),
                        act_ent_type=text(r, "act_ent_type"),
                    ))
                except Exception as e:
                    logger.warning("跳过无效行: %s", e)
        if len(errors) == len(_EXCHANGES):
            raise RuntimeError("stock_basic 全部交易所失败: " + "; ".join(errors))
        return out


__all__ = ["StockBasicTushareFetcher"]
