"""infrastructure.config — DI 工厂 + Settings

Lazy import di 模块，避免与 connection.py 形成循环 import。
"""
from infrastructure.config.settings import get_settings

__all__ = ["get_settings"]


def __getattr__(name):
    """PEP 562 — module-level __getattr__，按需加载 di 的内容"""
    if name in (
        "get_concept_brief_service",
        "get_indicator_calculator",
        "get_kline_app_service",
        "get_kline_fetcher",
        "get_panel_app_service",
    ):
        from infrastructure.config import di
        return getattr(di, name)
    raise AttributeError(f"module 'infrastructure.config' has no attribute {name!r}")
