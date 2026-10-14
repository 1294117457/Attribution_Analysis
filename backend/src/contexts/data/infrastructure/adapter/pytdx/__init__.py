"""pytdx（通达信）：Client + 分 K Adapter"""
from contexts.data.infrastructure.adapter.pytdx.client import PytdxClient
from contexts.data.infrastructure.adapter.pytdx.tech import ADAPTERS

__all__ = ["ADAPTERS", "PytdxClient"]
