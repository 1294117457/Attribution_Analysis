"""user context — DI 工厂聚合"""
from contexts.user.infrastructure.di.stock_pool import get_stock_pool_service

__all__ = ["get_stock_pool_service"]
