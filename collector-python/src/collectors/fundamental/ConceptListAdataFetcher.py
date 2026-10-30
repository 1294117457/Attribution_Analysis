"""ConceptListAdataFetcher：概念清单（同花顺 adata all_concept_code_ths）—— step7 重构版

返回 list[dict]（去 Port 化，service 自行入库）
"""
from __future__ import annotations

import logging
import math
from datetime import date, datetime
from typing import Optional

import pandas as pd

from pydantic import BaseModel

from collectors.base import BaseFetcher
from core.adata_client import get_adata_client

logger = logging.getLogger(__name__)


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
        # ★ ★ 单次调用，**不做内部重试**。
        #   上游「同花顺概念列表」会**间歇性返回空/残缺**（页面接口被限流时
        #   静默返回空 DataFrame，问财接口 token 过期时 index_code 整列变 NaN）。
        #   但重试**必须放在 service 层**（那里会先过 Redis 限流）：
        #   若在 fetcher 内重试，每次服务调用会放大成 N 次上游请求
        #   → 触发同花顺按 IP 限流 → 反而一直拿不到数据。
        df = await self._c.call(
            lambda: self._sdk.stock.info.all_concept_code_ths(),
            "all_concept_code_ths",
        )
        items: list[dict] = []
        seen: set[str] = set()
        missing_index = 0
        for row in _rows(df):
            index_code = _code(row.get("index_code"))
            concept_code = _code(row.get("concept_code"))
            name = _str(row.get("name"))
            # ★ ★ index_code 缺失时的兜底：
            #   adata 的 all_concept_code_ths() 由两个来源 merge而成：
            #     index_code ← 问财接口（search.10jqka.com.cn，需有效 sessionid/token）
            #     concept_code ← 网页接口（q.10jqka.com.cn/gn/，稳定可用）
            #   问财的 sessionid/token 过期时，index_code 会**整列变成 NaN**，
            #   而 concept_code 仍然 100% 有效。
            #   → 此时用 concept_code 兜底当业务键，避免整个概念清单采成 0 行。
            if not index_code:
                missing_index += 1
                index_code = concept_code
            if not index_code or not name or index_code in seen:
                continue
            seen.add(index_code)
            items.append({
                "index_code": index_code,
                "concept_code": concept_code,
                "name": name,
                "index_code_missing": not _code(row.get("index_code")),
            })
        if missing_index:
            logger.warning(
                "concept_list: 上游 index_code 缺失 %d/%d 行（问财 token 过期），"
                "已用 concept_code 兜底作为业务键",
                missing_index, len(items) + missing_index,
            )
        return items


__all__ = [
    "ConceptListAdataFetcher", "_rows", "_str", "_code", "_symbol",
    "_float", "_date", "_datetime", "_is_missing",
]
