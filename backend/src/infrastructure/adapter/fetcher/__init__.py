"""Fetcher 实现聚合层

按数据源组织的采集器实现 + parser（数据源字段 → BO 翻译层）。
parser 与 fetcher 共生：fetcher 调数据源 → 拿原始 DataFrame → 立即调 parser 转 BO，
生命周期一致（同数据源就用同 parser；数据源下线 parser 也下线）。
"""
from infrastructure.adapter.fetcher.adata import AdataConceptFetcher, AdataThrottledError
from infrastructure.adapter.fetcher.base import BaseCollector
from infrastructure.adapter.fetcher.pytdx import MinuteKlineBO, PytdxFetcher, PytdxKlineParser
from infrastructure.adapter.fetcher.tushare import (
    TushareFetcher,
    TushareKlineParser,
    dedupe_income,
    parse_list_date,
    symbol_to_ts_code,
)

__all__ = [
    "AdataConceptFetcher",
    "AdataThrottledError",
    "BaseCollector",
    "MinuteKlineBO",
    "PytdxFetcher",
    "PytdxKlineParser",
    "TushareFetcher",
    "TushareKlineParser",
    "dedupe_income",
    "parse_list_date",
    "symbol_to_ts_code",
]