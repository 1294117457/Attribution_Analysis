"""ConceptMembersAdataFetcher：概念成分股（同花顺 adata concept_constituent_ths）—— step7 重构版"""
from __future__ import annotations

from pydantic import BaseModel

from contexts.collect.infrastructure.fetcher.base import BaseFetcher
from contexts.collect.infrastructure.connect.adata_client import get_adata_client
from contexts.collect.infrastructure.fetcher.fundamental.ConceptListAdataFetcher import (
    _rows, _str, _symbol,
)


class ConceptMembersAdataFetcher(BaseFetcher):
    fetcher_type = "concept_members_adata"
    source = "adata"
    label = "概念成分股（同花顺 adata）"

    def __init__(self) -> None:
        self._c = get_adata_client()
        self._sdk = self._c.sdk

    async def fetch(self, **params) -> list[BaseModel]:
        index_code = params.get("index_code")
        if not index_code:
            raise ValueError("index_code 必填")
        df = await self._c.call(
            lambda: self._sdk.stock.info.concept_constituent_ths(index_code=index_code),
            "concept_constituent_ths",
        )
        items: list[dict] = []
        seen: set[str] = set()
        for row in _rows(df):
            sym = _symbol(row.get("stock_code"))
            if sym and sym not in seen:
                seen.add(sym)
                # §2.10 补 Adata concept_constituent_ths 文档 short_name 字段
                # source 固定为 ths（与 ORM 对齐），无 reason
                items.append({
                    "index_code": index_code,
                    "symbol": sym,
                    "short_name": _str(row.get("short_name")),
                    "source": "ths",
                })
        return items


__all__ = ["ConceptMembersAdataFetcher"]
