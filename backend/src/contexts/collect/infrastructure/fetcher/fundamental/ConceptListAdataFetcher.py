"""ConceptListAdataFetcher：概念清单（同花顺 adata all_concept_code_ths）—— step7 重构版

返回 list[dict]（去 Port 化，service 自行入库）
"""
from __future__ import annotations

import math
from datetime import date, datetime
from typing import Optional

import pandas as pd

from pydantic import BaseModel

from contexts.collect.infrastructure.fetcher.base import BaseFetcher
from contexts.collect.infrastructure.connect.adata_client import get_adata_client

logger = None  # 占位


def _rows(df) -> list[dict]:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return []
    return df.to_dict("records")


def _is_missing(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v)) or (isinstance(v, str) and not v.strip())


def _str(v) -> Optional[str]:
    if _is_missing(v):
        return None
    return str(v).strip() or None


def _code(v) -> Optional[str]:
    s = _str(v)
    if s is None:
        return None
    if s.endswith(".0"):
        s = s[:-2]
    return s


def _symbol(v) -> Optional[str]:
    s = _code(v)
    if s is None:
        return None
    s = s.zfill(6)
    return s if len(s) == 6 and s.isdigit() else None


def _float(v) -> Optional[float]:
    if _is_missing(v):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _date(v) -> Optional[date]:
    if _is_missing(v):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _datetime(v) -> Optional[datetime]:
    if _is_missing(v):
        return None
    if isinstance(v, datetime):
        return v
    try:
        return datetime.strptime(str(v)[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


class ConceptListAdataFetcher(BaseFetcher):
    fetcher_type = "concept_list_adata"
    source = "adata"
    label = "概念清单（同花顺 adata）"

    def __init__(self) -> None:
        self._c = get_adata_client()
        self._sdk = self._c.sdk

    async def fetch(self, **params) -> list[BaseModel]:
        df = await self._c.call(
            lambda: self._sdk.stock.info.all_concept_code_ths(),
            "all_concept_code_ths",
        )
        items: list[dict] = []
        seen: set[str] = set()
        for row in _rows(df):
            index_code = _code(row.get("index_code"))
            name = _str(row.get("name"))
            if not index_code or not name or index_code in seen:
                continue
            seen.add(index_code)
            items.append({
                "index_code": index_code,
                "concept_code": _code(row.get("concept_code")),
                "name": name,
                # §2.9 补 Adata all_concept_code_ths 文档 source 字段
                "source": _str(row.get("source")) or "ths",
            })
        return items


__all__ = [
    "ConceptListAdataFetcher", "_rows", "_str", "_code", "_symbol",
    "_float", "_date", "_datetime", "_is_missing",
]
