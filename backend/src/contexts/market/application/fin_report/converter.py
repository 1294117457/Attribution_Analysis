"""fin_report BO → Entity 转换器（step7-e 自动生成）"""
from __future__ import annotations


# FinReportBO → FinReport
from contexts.market.domain.fin_report.entity import FinReport

def fin_report_bo_to_entity(bo) -> "FinReport":
    return FinReport(**bo.model_dump())

