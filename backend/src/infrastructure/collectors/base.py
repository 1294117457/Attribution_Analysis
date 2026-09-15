"""采集器基类

提供采集器的通用功能：日志、错误处理、缓存。
"""

from __future__ import annotations

import logging
from abc import ABC

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """采集器基类"""

    def __init__(self):
        self._logger = logger
        self._cache: dict = {}

    def _log(self, level: str, message: str, **kwargs) -> None:
        extra = {"source": getattr(self, "source_name", "unknown")}
        extra.update(kwargs)
        getattr(self._logger, level)(message, extra=extra)

    def _wrap_error(self, message: str, original_error: Exception) -> RuntimeError:
        source = getattr(self, "source_name", "Collector")
        err = RuntimeError(f"{source}: {message}")
        err.__cause__ = original_error
        return err
