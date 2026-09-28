"""采集器基类

提供采集器的通用能力：
- 统一的 logger（避免每个 fetcher 重复 `self._logger = logging.getLogger(__name__)`）
- 统一的 source_name 注入
- 统一的错误包装（_wrap_error）

继承规则：
- 所有 fetcher 应当继承本类，无需再自行持有 logger / source_name
"""

from __future__ import annotations

import logging
from abc import ABC

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """采集器基类"""

    # 子类必须声明的数据源标识（如 'Tushare' / 'Pytdx' / 'Adata-THS'）
    SOURCE_NAME: str = "Unknown"

    def __init__(self):
        self._logger = logging.getLogger(type(self).__module__)

    @property
    def source_name(self) -> str:
        return self.SOURCE_NAME

    def _log(self, level: str, message: str, **kwargs) -> None:
        extra = {"source": self.source_name}
        extra.update(kwargs)
        getattr(self._logger, level)(message, extra=extra)

    def _wrap_error(self, message: str, original_error: Exception) -> RuntimeError:
        err = RuntimeError(f"{self.source_name}: {message}")
        err.__cause__ = original_error
        return err
