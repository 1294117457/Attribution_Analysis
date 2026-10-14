"""数据层：所有外部数据源（Tushare / adata / pytdx）的统一入口

调用方只依赖 application.port.data 里的 Port 与 DataGatewayPort；
本包负责 Adapter 实现、装配与 DataGateway 单例。
"""
from __future__ import annotations

from typing import Optional

from contexts.data.infrastructure.adapter.core import DataGateway, get_data_port_registry
from contexts.data.infrastructure.adapter.setup import setup_data

_gateway: Optional[DataGateway] = None


def get_data_gateway() -> DataGateway:
    global _gateway
    if _gateway is None:
        _gateway = DataGateway(setup_data(get_data_port_registry()))
    return _gateway


__all__ = ["DataGateway", "get_data_gateway", "setup_data"]
