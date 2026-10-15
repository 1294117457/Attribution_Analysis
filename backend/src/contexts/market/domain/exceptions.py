"""market 上下文领域异常统一出口（re-export 模式）

- 真正的异常类在各自的 entity 模块里定义（更靠近领域知识）
- 本文件只做 re-export，对外提供统一 import 路径
  from contexts.market.domain.exceptions import StockNotFoundError, KlineNotFoundError, ...
"""
from __future__ import annotations

# 股票相关
from contexts.market.domain.entities.stock_info.entity import StockNotFoundError

# K线相关
from contexts.market.domain.entities.kline.entity import (
    KlineNotFoundError,
    KlineDataError,
    CollectionError,
)

__all__ = [
    # 股票相关
    "StockNotFoundError",
    # K线相关
    "KlineNotFoundError",
    "KlineDataError",
    "CollectionError",
]
