"""统一异常（原 shared/domain/base.DomainError + port/errors + domain/exceptions 三合一）。

调用方只需关心三类：
  RateLimited       数据源限流（service 捕获后 sleep 重试）
  SourceUnavailable 数据源不可用（service 捕获后标记失败）
  DomainError       业务异常（HTTP 状态码由 exc.http_status 声明，见 main.py）
"""
from __future__ import annotations


class DomainError(Exception):
    """业务异常基类（message + code + http_status）

    ⚠️ code 必须是**数字**：前端 `unwrap()` 按 `d.code >= 400` 判错，
    字符串 code 会导致比较失败 → 错误被当成成功返回。
    """

    HTTP_BAD_REQUEST = 400
    HTTP_UNAUTHORIZED = 401
    HTTP_FORBIDDEN = 403
    HTTP_NOT_FOUND = 404
    HTTP_CONFLICT = 409
    HTTP_BAD_GATEWAY = 502
    HTTP_SERVICE_UNAVAILABLE = 503

    def __init__(self, message: str, code: int = 400, http_status: int = 400) -> None:
        self.message = message
        self.code = code
        self.http_status = http_status
        super().__init__(message)


class RateLimited(Exception):
    """数据源限流"""

    def __init__(self, message: str = "", retry_after: float = 60.0) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class SourceUnavailable(Exception):
    """数据源不可用"""


class SourceNotPermitted(SourceUnavailable):
    """数据源**账号权限不足**（不是代码 bug，重试无用）。

    Tushare 典型报文：「抱歉，您没有接口(limit_list_d)访问权限」。
    这类错误重试多少次都一样，必须与「临时不可用」区分开：
      - SourceUnavailable → 重试可能成功
      - SourceNotPermitted → 重试永远失败 → service 应记为 skip（跳过），
        任务终态仍为 done，并在 message 里说明「该接口无权限」。

    ⚠️ 判定必须基于上游报文的**特征串**，不要用整句匹配
      （上游文案会变，中英文都可能）。
    """

    #: Tushare 权限不足报文的特征子串（任一命中即判定为无权限）
    PERMISSION_MARKERS = (
        "没有接口",       # 「您没有接口(xxx)访问权限」
        "访问权限",
        "积分不够",       # 积分不足（部分接口按积分分级）
        "no access",      # 英文变体
        "permission denied",
    )

    @classmethod
    def is_permission_error(cls, msg: str) -> bool:
        m = (msg or "").lower()
        return any(k in m for k in cls.PERMISSION_MARKERS)


class InvalidParams(ValueError):
    """入参违反业务规则"""


class CollectorNotFound(DomainError):
    """collector 不存在（HTTP 404）

    专用异常类型，禁止用字符串匹配判断「不存在」——异常 message 一改，HTTP 状态码就跟着错。

    ⚠️ code 必须是**数字**：前端 `unwrap()` 按 `d.code >= 400` 判错，
    字符串 code 会导致比较失败 → 错误被当成成功返回。
    """

    def __init__(self, message: str) -> None:
        super().__init__(message, code=404, http_status=404)


class NotSupported(NotImplementedError):
    """当前数据源不支持该参数组合"""


__all__ = ["DomainError", "RateLimited", "SourceUnavailable", "SourceNotPermitted",
           "InvalidParams", "CollectorNotFound", "NotSupported"]
