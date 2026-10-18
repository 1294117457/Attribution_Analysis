"""全局异常处理器（统一 4 个：业务 / FastAPI 校验 / 数据源 / 兜底）

设计要点：
- 业务异常统一通过 DomainError 兜底，HTTP 状态码由异常自己声明（exc.http_status）
- FastAPI 内置的 RequestValidationError 单独处理（不属于 DomainError，但要走 422）
- KeyError 单独处理（启动配置缺失场景）
- Exception 兜底
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from shared.domain.base import DomainError

logger = logging.getLogger(__name__)


def _safe(value):
    """把 bytes 转 str，避免 JSON 序列化失败（处理 RequestValidationError）"""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            return repr(value)
    if isinstance(value, dict):
        return {k: _safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in value]
    return value


def register_exception_handlers(application: FastAPI) -> None:
    """注册 4 个全局异常处理器"""

    @application.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError):
        """业务域异常统一接住，HTTP 状态码由 exc.http_status 决定"""
        return JSONResponse(
            status_code=exc.http_status,
            content={"code": exc.code, "message": exc.message, "data": None},
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """FastAPI 内置的请求参数校验异常（422）"""
        return JSONResponse(
            status_code=422,
            content={
                "code": 422,
                "message": "请求参数校验失败",
                "data": {"errors": _safe(exc.errors())},
            },
        )

    @application.exception_handler(KeyError)
    async def registry_not_found_handler(request: Request, exc: KeyError):
        """注册中心未找到对应的协议实现（启动配置缺失）"""
        logger.error("数据源未注册: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"code": 503, "message": f"数据源未配置: {exc}", "data": None},
        )

    @application.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        """兜底"""
        logger.exception("未处理的异常: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": "服务器内部错误", "data": None},
        )
