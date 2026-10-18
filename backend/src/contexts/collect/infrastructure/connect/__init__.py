"""collect.infrastructure.connect — 第三方数据源 SDK 客户端（单例）

包含：
- tushare_client:  TushareClient + get_tushare_client
- adata_client:    AdataClient + get_adata_client
- pytdx_client:    PytdxClient + get_pytdx_client

fetcher / service 通过 `from contexts.collect.infrastructure.connect.xxx_client import get_xxx_client`
获取单例 —— 不走 DI 注入，由 fetcher 内部按需 lazy init。
"""
from contexts.collect.infrastructure.connect.adata_client import (
    AdataClient,
    get_adata_client,
)
from contexts.collect.infrastructure.connect.pytdx_client import (
    PytdxClient,
    TDX_HOSTS,
    get_pytdx_client,
)
from contexts.collect.infrastructure.connect.tushare_client import (
    TushareClient,
    get_tushare_client,
)

__all__ = [
    "TushareClient",
    "AdataClient",
    "PytdxClient",
    "TDX_HOSTS",
    "get_tushare_client",
    "get_adata_client",
    "get_pytdx_client",
]
