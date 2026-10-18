"""contexts.collect.domain — 领域层（零外部依赖）

- entitys/    一个聚合根一个子目录
- exceptions.py  业务级异常统一出口（参考 market/domain/exceptions.py）
"""
from __future__ import annotations

from contexts.collect.domain.exceptions import (
    InvalidParams,
    NotSupported,
)

__all__ = [
    "InvalidParams",
    "NotSupported",
]
