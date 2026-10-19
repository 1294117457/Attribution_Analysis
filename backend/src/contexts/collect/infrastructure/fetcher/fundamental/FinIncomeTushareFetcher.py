"""FinIncomeTushareFetcher - Tushare income (step7 refactor)"""
from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict

from contexts.collect.application.bo import FinReportBO
from contexts.collect.infrastructure.fetcher.base import BaseFetcher
from contexts.collect.infrastructure.parser.tushare import (
    num, parse_list_date, rows, symbol_of, symbol_to_ts_code, text,
)
from contexts.collect.infrastructure.connect.tushare_client import get_tushare_client
from shared.interface.validators import Symbol

logger = logging.getLogger(__name__)


class FinIncomeParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: Symbol


class FinIncomeTushareFetcher(BaseFetcher):
    fetcher_type = "fin_income_tushare"
    source = "tushare"
    label = "Fin Income (Tushare)"

    def __init__(self) -> None:
        self._c = get_tushare_client()

    async def fetch(self, **params) -> list[BaseModel]:
        p = FinIncomeParams.model_validate(params)
        df = await self._c.query("income", ts_code=symbol_to_ts_code(p.symbol))
        out: list[FinReportBO] = []
        for r in rows(df):
            sym, ed = symbol_of(r), parse_list_date(r.get("end_date"))
            if not sym or not ed:
                continue
            out.append(FinReportBO(
                symbol=sym, end_date=ed,
                ann_date=parse_list_date(r.get("ann_date")),
                report_type=text(r, "report_type"),
                comp_type=text(r, "comp_type"),
                # §1.5 补 Tushare income 文档 end_type 字段
                end_type=text(r, "end_type"),
                basic_eps=num(r, "basic_eps"),
                diluted_eps=num(r, "diluted_eps"),
                total_revenue=num(r, "total_revenue"),
                revenue=num(r, "revenue"),
                operate_profit=num(r, "operate_profit"),
                total_profit=num(r, "total_profit"),
                n_income=num(r, "n_income"),
                n_income_attr_p=num(r, "n_income_attr_p"),
            ))
        return out


__all__ = ["FinIncomeParams", "FinIncomeTushareFetcher"]
