"""HTTP 异常处理器"""

import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("api.errors")


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """统一处理 HTTP 异常，返回标准格式"""
    logger.warning("HTTP %d: %s %s", exc.status_code, request.method, request.url.path)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """捕获未处理的服务端异常，避免暴露堆栈信息"""
    logger.exception("Unhandled exception: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status_code": 500},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """在 FastAPI 应用上注册所有异常处理器"""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
