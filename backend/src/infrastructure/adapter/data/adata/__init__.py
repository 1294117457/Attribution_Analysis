"""adata（同花顺）：Client + 6 个概念 Adapter"""
from infrastructure.adapter.data.adata.client import AdataClient
from infrastructure.adapter.data.adata.concept import ADAPTERS

__all__ = ["ADAPTERS", "AdataClient"]
