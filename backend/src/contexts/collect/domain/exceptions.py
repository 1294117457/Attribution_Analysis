"""contexts.collect.domain — 业务级异常统一出口

- 真正的异常类在本文件定义（业务级）
- 对外提供统一 import 路径：from contexts.collect.domain import InvalidParams, NotSupported

注意区分：
  - 业务规则异常（这里）：领域知识，参数/能力合规类
  - port 契约错误（application/port/errors.py）：RateLimited / SourceUnavailable
    这两类由 SDK 错误翻译而来，调用方据此决定 重试 / 换源 / 降级
"""
from __future__ import annotations

from shared.domain.base import DomainError


class InvalidParams(DomainError):
    """入参非法（业务规则约束违反）

    与 pydantic ValidationError 的区别：pydantic 校验字段类型/格式；
    本异常校验业务级约束（如"上市公司不能被删除"）。

    ★ 继承 DomainError 而非 ValueError：全局异常处理器按 DomainError
      统一转 HTTP 400，所以 service 层的业务校验可以「直接往上抛」，
      route 层不需要写 try/except 手工转状态码（v7 起 daily 路由即如此）。
    """

    def __init__(self, message: str, code: str = "INVALID_PARAMS"):
        super().__init__(message, code=code, http_status=self.HTTP_BAD_REQUEST)


class NotSupported(DomainError):
    """service / fetcher 不支持某种参数组合或操作

    区别于 NotImplementedError：明确表示「接口设计上有这个能力，
    但当前数据源/实现不支持」，调用方可以尝试换源。
    """

    def __init__(self, message: str, code: str = "NOT_SUPPORTED"):
        super().__init__(message, code=code, http_status=self.HTTP_BAD_REQUEST)


__all__ = [
    "InvalidParams",
    "NotSupported",
]
