"""Tushare Adapter 公共的实现方属性"""
from __future__ import annotations

from contexts.data.infrastructure.adapter.core.base import AdapterBase
from contexts.data.infrastructure.adapter.tushare.client import TushareClient


class TushareAdapterBase(AdapterBase):
    tool = "tushare"
    origin = "tushare"
    priority = 10
    throttle_group = "tushare"

    def __init__(self, client: TushareClient) -> None:
        self._c = client


__all__ = ["TushareAdapterBase"]
