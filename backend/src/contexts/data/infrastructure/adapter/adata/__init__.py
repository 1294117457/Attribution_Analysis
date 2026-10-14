"""adata（同花顺）：Client + 6 个概念 Adapter"""
from contexts.data.infrastructure.adapter.adata.client import AdataClient
from contexts.data.infrastructure.adapter.adata.concept import ADAPTERS

__all__ = ["ADAPTERS", "AdataClient"]
