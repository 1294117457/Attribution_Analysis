"""market context — DI 工厂聚合"""
from contexts.market.infrastructure.di.stock_info import get_stock_info_service

__all__ = ["get_stock_info_service"]
